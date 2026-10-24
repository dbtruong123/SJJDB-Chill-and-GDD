"""HTTP API for the grower dashboard.

For the five CIMIS stations, and any orchard location between them, it serves chill and GDD
so far this season, how that compares with past seasons on the same date, the daily 7-day
forecast and the map grid. With CIMIS_APP_KEY set it pulls fresh readings at start-up and
every 6 hours; without it, it serves the forecast from the last day in the hourly file.

    cd forecast
    export CIMIS_APP_KEY=...          # optional, never commit it
    uvicorn api:app --port 8000       # interactive docs at http://127.0.0.1:8000/docs

Needs the trained model (`python daily_forecast.py train`).

Endpoints (all GET return JSON; `measure` is gdd, chill_portions or chill_hours):
    GET  /api/health
    GET  /api/stations
    GET  /api/stations/{station}/summary?measure=gdd
    GET  /api/stations/{station}/seasons?measure=gdd
    GET  /api/forecast[?station=6]
    GET  /api/map?measure=gdd&value=next7          (value: next7, season_to_date, projected)
    GET  /api/point?lat=37.6&lon=-120.9&measure=gdd
    POST /api/refresh
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import daily_forecast as dfc
from baselines import daily_from_hourly, haversine_km, load_hourly
from dashboard_data import CORRIDOR_KM, corridor_grid, weights
from map_loso import dist_matrix, kriging_weights
import agro  # noqa: E402,I001  (importing baselines puts cimis_puller on sys.path)

Measure = Literal["gdd", "chill_portions", "chill_hours"]
SEASON_START = {"chill_hours": "11-01", "chill_portions": "11-01", "gdd": "01-01"}
UNITS = {"chill_hours": "hours", "chill_portions": "portions", "gdd": "degree-days (F)"}
REFRESH_HOURS = 6
LIVE_DAYS = 21


@dataclass(frozen=True)
class Snapshot:
    """Everything one forecast run produced; swapped whole so requests never see a half update."""
    hourly_path: object
    daily: pd.DataFrame
    forecast: pd.DataFrame
    issue: pd.Timestamp
    source: str
    refreshed_at: str


class State:
    def __init__(self) -> None:
        if not dfc.MODEL_PATH.exists():
            raise RuntimeError(f"{dfc.MODEL_PATH} not found: run `python daily_forecast.py train` first")
        self.bundle = dfc.load_model()
        self.stations = pd.read_csv(dfc.DEFAULT_STATIONS).sort_values("station").reset_index(drop=True)
        self.d_oo = dist_matrix(self.stations)
        self.grid = weights(corridor_grid(self.stations), self.stations)
        self.refresh_lock = threading.Lock()
        self.last_error: str | None = None
        start = dfc.LIVE_HOURLY if dfc.LIVE_HOURLY.exists() else dfc.DEFAULT_HOURLY
        self.snap = self._build(start, "live file" if start == dfc.LIVE_HOURLY else "archive")

    def _build(self, path, source: str) -> Snapshot:
        daily = daily_from_hourly(load_hourly(path))
        fc = dfc.forecast_frame(daily, self.stations, self.bundle)
        return Snapshot(path, daily, fc, fc["issue_date"].iloc[0], source,
                        datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def refresh(self) -> None:
        key = os.environ.get("CIMIS_APP_KEY")
        if not key:
            raise RuntimeError("CIMIS_APP_KEY is not set on the server")
        with self.refresh_lock:
            try:
                fresh = dfc.fetch_live(self.stations, LIVE_DAYS, key)
            except SystemExit as e:  # fetch_live exits with a message when CIMIS returns nothing
                raise RuntimeError(str(e)) from None
            path = dfc.merge_live(self.snap.hourly_path, fresh)
            self.snap = self._build(path, "CIMIS API")
            self.last_error = None

    def refresh_forever(self) -> None:
        while True:
            try:
                self.refresh()
            except Exception as e:  # keep serving the last good forecast
                self.last_error = f"{type(e).__name__}: {e}"
            time.sleep(REFRESH_HOURS * 3600)


state: State | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global state
    state = State()
    if os.environ.get("CIMIS_APP_KEY"):
        threading.Thread(target=state.refresh_forever, daemon=True).start()
    yield


app = FastAPI(title="Valley Chill & GDD API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _num(x, nd: int = 2):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def _day(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _label(season: int, c: str) -> str:
    return f"{season}-{str(season + 1)[-2:]}" if SEASON_START[c] == "11-01" else str(season)


def _season_start(day: pd.Timestamp, c: str) -> tuple[int, pd.Timestamp]:
    season = int(agro.season_id(pd.Series([day]), SEASON_START[c]).iloc[0])
    m, d = (int(v) for v in SEASON_START[c].split("-"))
    return season, pd.Timestamp(season, m, d)


def _check_station(station: int) -> None:
    if station not in set(state.stations["station"]):
        raise HTTPException(404, f"unknown station {station}; see /api/stations")


def _station_series(snap: Snapshot, station: int, c: str) -> pd.Series:
    return snap.daily[snap.daily["station"] == station].set_index("date")[c].sort_index()


def _summary(snap: Snapshot, station: int, c: str) -> dict:
    obs = _station_series(snap, station, c)
    season, s0 = _season_start(snap.issue, c)
    offset = (snap.issue - s0).days
    now = obs[s0:snap.issue]
    fc = snap.forecast[snap.forecast["station"] == station].sort_values("target_date")
    clim = state.bundle["climatology"]
    doy = fc["target_date"].dt.dayofyear.clip(upper=365)
    normal = clim[clim["station"] == station].set_index("doy")[f"clim_{c}"]
    past = []
    for k in range(1, 10):
        p0 = s0 - pd.DateOffset(years=k)
        if p0 < obs.index.min():
            break
        span = obs[p0:p0 + pd.Timedelta(days=offset)]
        if span.notna().sum() >= 0.9 * (offset + 1):
            past.append({"season": _label(season - k, c), "total": _num(span.sum())})
    past_avg = float(np.mean([p["total"] for p in past])) if past else None
    so_far = float(now.sum())
    return {
        "station": station, "measure": c, "units": UNITS[c],
        "issue_date": _day(snap.issue), "season": _label(season, c), "season_start": _day(s0),
        "season_to_date": _num(so_far), "days_missing": int(now.isna().sum()),
        "next7": _num(fc[c].sum()), "normal_next7": _num(normal.reindex(doy).sum()),
        "projected": _num(fc[f"{c}_season_to_date"].iloc[-1]),
        "projected_through": _day(fc["target_date"].iloc[-1]),
        "past_seasons_same_date": past, "past_avg_same_date": _num(past_avg),
        "pct_vs_past": _num(100 * (so_far / past_avg - 1), 1) if past_avg else None,
    }


@app.get("/api/health")
def health() -> dict:
    snap = state.snap
    return {"status": "ok", "issue_date": _day(snap.issue), "source": snap.source,
            "refreshed_at": snap.refreshed_at, "live_updates": bool(os.environ.get("CIMIS_APP_KEY")),
            "model_trained_through": state.bundle["trained_through"], "last_error": state.last_error}


@app.get("/api/stations")
def stations() -> list[dict]:
    return [{"station": int(r["station"]), "name": r["name"], "latitude": _num(r["latitude"], 5),
             "longitude": _num(r["longitude"], 5), "elevation_ft": _num(r["elevation_ft"])}
            for _, r in state.stations.iterrows()]


@app.get("/api/stations/{station}/summary")
def summary(station: int, measure: Measure = "gdd") -> dict:
    _check_station(station)
    return _summary(state.snap, station, measure)


@app.get("/api/stations/{station}/seasons")
def seasons(station: int, measure: Measure = "gdd") -> dict:
    """Running season totals: this season (observed, then forecast) and each past season."""
    _check_station(station)
    snap, c = state.snap, measure
    obs = _station_series(snap, station, c)
    season, s0 = _season_start(snap.issue, c)
    out = []
    for k in range(0, 10):
        p0 = s0 - pd.DateOffset(years=k)
        if p0 < obs.index.min():
            break
        end = snap.issue if k == 0 else p0 + pd.DateOffset(years=1) - pd.Timedelta(days=1)
        run = obs[p0:end].fillna(0).cumsum()
        points = [{"day": (d - p0).days, "date": _day(d), "total": _num(v), "kind": "observed"}
                  for d, v in run.items()]
        if k == 0:
            fc = snap.forecast[(snap.forecast["station"] == station)].sort_values("target_date")
            fc = fc[agro.season_id(fc["target_date"], SEASON_START[c]) == season]
            points += [{"day": (d - p0).days, "date": _day(d), "total": _num(v), "kind": "forecast"}
                       for d, v in zip(fc["target_date"], fc[f"{c}_season_to_date"])]
        out.append({"season": _label(season - k, c), "current": k == 0, "points": points})
    return {"station": station, "measure": c, "units": UNITS[c], "issue_date": _day(snap.issue),
            "seasons": out}


@app.get("/api/forecast")
def forecast(station: int | None = None) -> list[dict]:
    """The daily 7-day forecast, one row per station and day, with season-to-date totals."""
    fc = state.snap.forecast
    if station is not None:
        _check_station(station)
        fc = fc[fc["station"] == station]
    return [{"station": int(r["station"]), "issue_date": _day(r["issue_date"]),
             "target_date": _day(r["target_date"]), "horizon": int(r["horizon"]),
             **{k: _num(r[k]) for k in fc.columns if k.startswith(("chill", "gdd"))}}
            for _, r in fc.sort_values(["station", "target_date"]).iterrows()]


@app.get("/api/map")
def map_grid(measure: Measure = "gdd",
             value: Literal["next7", "season_to_date", "projected"] = "next7") -> dict:
    """Grid points about 5 km apart between the stations; each value is a kriging-weighted mix of stations."""
    snap = state.snap
    ids = state.stations["station"].tolist()
    per_station = {s: _summary(snap, s, measure)[value] for s in ids}
    w = state.grid[[f"w_{s}" for s in ids]].to_numpy()
    vals = w @ np.array([per_station[s] or 0.0 for s in ids])
    return {"measure": measure, "value": value, "units": UNITS[measure], "issue_date": _day(snap.issue),
            "stations": [{"station": s, "value": per_station[s]} for s in ids],
            "points": [{"lat": float(la), "lon": float(lo), "value": _num(v), "nearest_km": float(nk)}
                       for la, lo, v, nk in zip(state.grid["latitude"], state.grid["longitude"], vals,
                                                state.grid["nearest_km"])]}


@app.get("/api/point")
def point(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
          measure: Measure = "gdd") -> dict:
    """Estimate for any orchard location: the same numbers as a station summary, kriged from the five."""
    snap, st = state.snap, state.stations
    d_os = haversine_km(lat, lon, st["latitude"].to_numpy(), st["longitude"].to_numpy())
    w = (d_os == d_os.min()).astype(float) if d_os.min() < 0.5 else kriging_weights(state.d_oo, d_os)
    ids = st["station"].tolist()
    sums = [_summary(snap, s, measure) for s in ids]
    mix = lambda key: _num(sum(wi * (s[key] or 0.0) for wi, s in zip(w, sums)))  # noqa: E731
    fc = snap.forecast.pivot(index="target_date", columns="station", values=measure)[ids]
    nearest = int(np.argmin(d_os))
    return {"lat": lat, "lon": lon, "measure": measure, "units": UNITS[measure],
            "issue_date": _day(snap.issue),
            "nearest_station": int(ids[nearest]), "nearest_km": _num(d_os.min(), 1),
            "rough_estimate": bool(d_os.min() > CORRIDOR_KM),
            "weights": {str(s): _num(x, 3) for s, x in zip(ids, w)},
            "season_to_date": mix("season_to_date"), "next7": mix("next7"),
            "normal_next7": mix("normal_next7"), "projected": mix("projected"),
            "past_avg_same_date": mix("past_avg_same_date"),
            "daily": [{"date": _day(d), measure: _num(row @ w)} for d, row in zip(fc.index, fc.to_numpy())]}


@app.post("/api/refresh")
def refresh() -> dict:
    """Pull the last 3 weeks from CIMIS now and re-forecast (it also runs every 6 hours on its own)."""
    if not os.environ.get("CIMIS_APP_KEY"):
        raise HTTPException(400, "CIMIS_APP_KEY is not set on the server")
    try:
        state.refresh()
    except Exception as e:
        state.last_error = f"{type(e).__name__}: {e}"
        raise HTTPException(502, f"refresh failed, still serving the last forecast: {e}") from None
    return health()
