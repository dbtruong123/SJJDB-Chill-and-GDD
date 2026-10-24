"""Pipeline: CIMIS stations -> one unified, ML-ready CSV.

Default stations: 6 Davis (Yolo), 70 Manteca (San Joaquin), 71 Modesto
(Stanislaus), 39 Parlier (Fresno), 5 Shafter (Kern).

Steps (per station, sequentially):
  1. Resolve stations (by number, or the nearest one to a lat/lon).
  2. Request the date range from the CIMIS API in chunks under the record cap.
  3. Combine, sort, de-duplicate, and re-index onto the full date (or hour)
     range so gaps are explicit rows.
  3b. (daily scope) Also pull hourly air temperature and add chill and GDD
     columns per day; see agro.py and add_agro_columns below.
Then for all stations together:
  4. Make it ML-ready: numeric features, QC codes plus 0/1 flags, time
     features, units moved to a sidecar JSON.
  5. Write one CSV (long: one row per station x timestamp; or --wide: one row
     per timestamp with station-prefixed columns, for neighbor-based models).

Usage:
    export CIMIS_APP_KEY=your-key
    python pipeline.py                                  # the 5 default stations
    python pipeline.py --stations 6,70,71,39,5 --wide --out data/train.csv
    python pipeline.py --gdd-base 45,50 --chill-start 10-01
    python pipeline.py --lat 38.54 --lon -121.78 --scope hourly
    python pipeline.py --stations 2 --start 2022-01-01 --end 2022-12-31

Default window is Sep 1 2021 to Sep 30 2026. Builds on cimis_pull.py (same
folder) for the API client and parsing.

In a notebook (see cimis_dataset.ipynb):
    from pipeline import build_dataset
    df, units = build_dataset(client)        # DataFrame, no CSV needed
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd

import agro
import cimis_pull as cp

DEFAULT_STATIONS = [6, 70, 71, 39, 5]
DEFAULT_START = date(2021, 9, 1)
DEFAULT_END = date(2026, 9, 30)

DROP_COLS = ("date", "hour", "julian", "station", "standard", "zip_codes", "scope")


def nearest_station(stations: list[cp.Station], lat: float, lon: float,
                    start: date, end: date) -> tuple[cp.Station, float]:
    """Closest station (great-circle km) that was operating during [start, end]."""
    def km(s: cp.Station) -> float:
        p1, p2 = math.radians(lat), math.radians(s.latitude)
        dp, dl = p2 - p1, math.radians(s.longitude - lon)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(a))

    candidates = [s for s in stations if s.latitude is not None and s.longitude is not None
                  and s.operating_during(start, end)]
    if not candidates:
        raise SystemExit("no station with coordinates operated in that window")
    best = min(candidates, key=km)
    return best, km(best)


def resolve_stations(client: cp.CimisClient, numbers: list[int] | None, lat: float | None,
                     lon: float | None, start: date, end: date, log=print) -> list[cp.Station]:
    stations = client.stations()
    if numbers:
        by_num = {s.number: s for s in stations}
        missing = [n for n in numbers if n not in by_num]
        if missing:
            raise SystemExit(f"station(s) {missing} not found in CIMIS station list")
        chosen = [by_num[n] for n in numbers]
    else:
        st, dist = nearest_station(stations, lat, lon, start, end)
        log(f"nearest station to ({lat}, {lon}) is {st.number} {st.name}, {dist:.1f} km away")
        chosen = [st]
    for st in chosen:
        if not st.operating_during(start, end):
            log(f"warning: station {st.number} was not operating for the whole window "
                f"(connected {st.connect_date}, disconnected {st.disconnect_date})")
    return chosen


def fetch(client: cp.CimisClient, st: cp.Station, start: date, end: date,
          scope: str, unit: str, log=print, items: list[str] | None = None) -> pd.DataFrame:
    items = items or (cp.DAILY_ITEMS if scope == "daily" else cp.HOURLY_ITEMS)
    chunks = cp.date_chunks(start, end, 1 if scope == "daily" else 24)
    rows = []
    for i, (a, b) in enumerate(chunks, 1):
        got = client.data(st.number, a, b, items, unit)
        log(f"  request {i}/{len(chunks)}: {a} to {b}, {len(got)} records")
        rows.extend(got)
    return pd.DataFrame(rows)


def build_table(raw: pd.DataFrame, st: cp.Station, start: date, end: date,
                scope: str) -> pd.DataFrame:
    """One station's chunks -> one clean, gap-explicit table."""
    if raw.empty:
        raw = pd.DataFrame(columns=["date"] + (["hour"] if scope == "hourly" else []))

    if scope == "daily":
        raw["timestamp"] = pd.to_datetime(raw["date"])
        full = pd.date_range(start, end, freq="D")
    else:
        # CIMIS hours run 0100..2400; 2400 is midnight at the end of that date.
        hrs = pd.to_numeric(raw["hour"], errors="coerce") // 100
        raw["timestamp"] = pd.to_datetime(raw["date"]) + pd.to_timedelta(hrs, unit="h")
        full = pd.date_range(pd.Timestamp(start) + pd.Timedelta(hours=1),
                             pd.Timestamp(end) + pd.Timedelta(days=1), freq="h")

    df = (raw.drop_duplicates(subset="timestamp", keep="last")
             .set_index("timestamp")
             .reindex(full))
    df.index.name = "timestamp"
    df["record_missing"] = df["date"].isna()  # True where CIMIS returned nothing
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

    meta = {"station": st.number, "station_name": st.name, "latitude": st.latitude,
            "longitude": st.longitude, "elevation_ft": st.elevation_ft}
    for i, (k, v) in enumerate(meta.items()):
        df.insert(i, k, v)
    return df.reset_index()


def add_agro_columns(daily: pd.DataFrame, hourly: pd.DataFrame, unit: str,
                     gdd_bases: list[float], chill_start: str, gdd_start: str) -> pd.DataFrame:
    """Add chill and GDD columns to one station's daily table.

    hourly is that station's build_table(..., "hourly") output, requested in
    English units so hly_air_tmp is already Fahrenheit. Daily max/min are
    converted to F when the daily data is metric. Added columns:
      hourly_temp_count / hourly_temp_flagged  valid / QC-flagged hours that day
      chill_hours, chill_units_utah, chill_portions    daily totals
      chill_season, *_cum                       running totals, reset on chill_start
      gdd_b<base>, gdd_b<base>_cum              per base temp (F), reset on gdd_start
    Daily totals are NaN when no hourly reading exists for the day. A day with
    only some hours still gets a total, so check hourly_temp_count.
    """
    h = hourly[["timestamp", "hly_air_tmp", "hly_air_tmp_qc"]].copy()
    # CIMIS hour 2400 is the last hour of its date, so shift back 1h to bucket by day.
    h["day"] = (h["timestamp"] - pd.Timedelta(hours=1)).dt.normalize()
    sid = agro.season_id(h["day"], chill_start)
    t = h["hly_air_tmp"].astype(float)
    h["chill_hours"] = agro.chill_hours(t)
    h["chill_units_utah"] = agro.utah_chill_units(t)
    h["chill_portions"] = agro.dynamic_chill_portions(t, reset=sid.ne(sid.shift()))
    h["flagged"] = h["hly_air_tmp_qc"].fillna("").astype(str).str.strip().ne("") & t.notna()

    chill_cols = ["chill_hours", "chill_units_utah", "chill_portions"]
    g = h.groupby("day")
    per_day = g[chill_cols].sum(min_count=1)
    per_day["hourly_temp_count"] = g["hly_air_tmp"].count()
    per_day["hourly_temp_flagged"] = g["flagged"].sum()

    out = daily.merge(per_day, left_on="timestamp", right_index=True, how="left")
    out["hourly_temp_count"] = out["hourly_temp_count"].fillna(0).astype(int)
    out["hourly_temp_flagged"] = out["hourly_temp_flagged"].fillna(0).astype(int)

    out["chill_season"] = agro.season_id(out["timestamp"], chill_start)
    for c in chill_cols:
        out[f"{c}_cum"] = out.groupby("chill_season")[c].cumsum()

    tmax, tmin = out["day_air_tmp_max"].astype(float), out["day_air_tmp_min"].astype(float)
    if unit == "M":
        tmax, tmin = agro.c_to_f(tmax), agro.c_to_f(tmin)
    gdd_season = agro.season_id(out["timestamp"], gdd_start)
    for base in gdd_bases:
        col = f"gdd_b{base:g}"
        out[col] = agro.gdd(tmax, tmin, base)
        out[f"{col}_cum"] = out[col].groupby(gdd_season).cumsum()
    return out


def make_ml_ready(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Long table of all stations -> ML-ready table plus a {feature: unit} map.

    For each measurement X the output has:
      X          float, NaN when missing
      X_qc       CIMIS QC code as text ("" = passed; e.g. M, R, Y, Q are flags)
      X_flag     1 if CIMIS flagged or nothing was recorded, else 0
    Plus row-level n_flags, record_missing (0/1), and month / day_of_year /
    hour time features. Units go to the returned map instead of a column.
    """
    df = df.copy()
    unit_cols = [c for c in df.columns if c.endswith("_unit")]
    units = {}
    for c in unit_cols:
        vals = df[c].dropna().unique()
        if len(vals):
            units[c[:-len("_unit")]] = str(vals[0])
    df = df.drop(columns=unit_cols)

    features = [c[:-len("_qc")] for c in df.columns if c.endswith("_qc")]
    for f in features:
        df[f] = pd.to_numeric(df[f], errors="coerce")
        df[f"{f}_qc"] = df[f"{f}_qc"].fillna("").astype(str).str.strip()
        df[f"{f}_flag"] = ((df[f"{f}_qc"] != "") | df[f].isna()).astype(int)
    df["n_flags"] = df[[f"{f}_flag" for f in features]].sum(axis=1) if features else 0
    df["record_missing"] = df["record_missing"].astype(bool).astype(int)

    ts = pd.to_datetime(df["timestamp"])
    df.insert(1, "month", ts.dt.month)
    df.insert(2, "day_of_year", ts.dt.dayofyear)
    if (ts.dt.hour != 0).any():
        df.insert(3, "hour", ts.dt.hour)

    # Stable column order: ids, time, station meta, then feature/qc/flag triples.
    lead = [c for c in ("timestamp", "month", "day_of_year", "hour", "station",
                        "station_name", "latitude", "longitude", "elevation_ft") if c in df.columns]
    body = [c for f in features for c in (f, f"{f}_qc", f"{f}_flag")]
    tail = [c for c in df.columns if c not in lead and c not in body]
    df = df[lead + body + tail].sort_values(["station", "timestamp"], kind="stable")
    return df.reset_index(drop=True), units


def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """One row per timestamp; every per-station column becomes s<num>_<col>."""
    time_cols = [c for c in ("timestamp", "month", "day_of_year", "hour") if c in df.columns]
    static = ["station_name", "latitude", "longitude", "elevation_ft"]
    value_cols = [c for c in df.columns if c not in time_cols + static + ["station"]]
    wide = df.pivot(index=time_cols, columns="station", values=value_cols)
    wide.columns = [f"s{st}_{col}" for col, st in wide.columns]
    order = sorted(wide.columns, key=lambda c: (int(c.split("_")[0][1:]), value_cols.index(c.split("_", 1)[1])))
    return wide[order].reset_index()


def build_dataset(client: cp.CimisClient, stations: list[int] | None = None,
                  lat: float | None = None, lon: float | None = None,
                  start: date = DEFAULT_START, end: date = DEFAULT_END,
                  scope: str = "daily", unit: str = "M", wide: bool = False,
                  agro_cols: bool = True, gdd_bases: tuple[float, ...] = (50.0,),
                  chill_start: str = "11-01", gdd_start: str = "01-01",
                  log=print) -> tuple[pd.DataFrame, dict]:
    """Pull every station from CIMIS and return (dataframe, units). No files written."""
    if stations is None and lat is None:
        stations = DEFAULT_STATIONS
    chosen = resolve_stations(client, stations, lat, lon, start, end, log)
    with_agro = agro_cols and scope == "daily"
    tables = []
    for i, st in enumerate(chosen, 1):
        log(f"[{i}/{len(chosen)}] station {st.number} {st.name}, {start} to {end} ({scope})")
        table = build_table(fetch(client, st, start, end, scope, unit, log), st, start, end, scope)
        if with_agro:
            log("  hourly air temperature for chill:")
            hourly = build_table(fetch(client, st, start, end, "hourly", "E", log,
                                       items=["hly-air-tmp"]), st, start, end, "hourly")
            table = add_agro_columns(table, hourly, unit, list(gdd_bases), chill_start, gdd_start)
        tables.append(table)

    df, units = make_ml_ready(pd.concat(tables, ignore_index=True))
    if with_agro:
        units.update({"chill_*": "hours / Utah units / Dynamic-model portions",
                      "gdd_*": "degree-days F (base in column name)"})
    if wide:
        df = to_wide(df)
    return df, units


def run(client: cp.CimisClient, out: Path | None, stations: list[int] | None = None,
        lat: float | None = None, lon: float | None = None,
        start: date = DEFAULT_START, end: date = DEFAULT_END,
        scope: str = "daily", unit: str = "M", wide: bool = False, log=print,
        **agro_kw) -> Path:
    table, units = build_dataset(client, stations, lat, lon, start, end, scope, unit,
                                 wide, log=log, **agro_kw)

    if out is None:
        ids = f"near{lat}_{lon}" if lat is not None else "-".join(map(str, stations or DEFAULT_STATIONS))
        out = Path("data") / f"cimis_{ids}_{scope}_{start:%Y%m}_{end:%Y%m}{'_wide' if wide else ''}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".csv.part")
    table.to_csv(tmp, index=False)
    tmp.replace(out)
    out.with_name(out.stem + "_units.json").write_text(
        json.dumps({"unit_system": "metric" if unit == "M" else "english", "units": units}, indent=2))

    log(f"wrote {len(table)} rows x {table.shape[1]} columns to {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    loc = p.add_mutually_exclusive_group()
    loc.add_argument("--stations", "--station",
                     help="comma-separated CIMIS station numbers (default: 6,70,71,39,5)")
    loc.add_argument("--lat", type=float, help="latitude; use with --lon to pick the nearest station")
    p.add_argument("--lon", type=float)
    p.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    p.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    p.add_argument("--scope", choices=["daily", "hourly"], default="daily")
    p.add_argument("--units", choices=["M", "E"], default="M", help="M=metric, E=English")
    p.add_argument("--wide", action="store_true", help="one row per timestamp, station-prefixed columns")
    p.add_argument("--out", type=Path)
    p.add_argument("--no-agro", action="store_true", help="skip chill/GDD (and the hourly pulls they need)")
    p.add_argument("--gdd-base", default="50", help="GDD base temps in F, comma-separated, e.g. 45,50")
    p.add_argument("--chill-start", default="11-01", help="MM-DD the chill season resets")
    p.add_argument("--gdd-start", default="01-01", help="MM-DD the GDD season resets")
    p.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--app-key", default=os.environ.get("CIMIS_APP_KEY"))
    a = p.parse_args(argv)

    if a.lat is not None and a.lon is None:
        p.error("--lat needs --lon")
    if a.start > a.end:
        p.error("--start is after --end")
    if not a.app_key:
        p.error("set CIMIS_APP_KEY or pass --app-key (get one at https://et.water.ca.gov)")
    stations = [int(s) for s in a.stations.split(",")] if a.stations else None

    run(cp.CimisClient(a.app_key, pause=a.pause), a.out, stations, a.lat, a.lon,
        a.start, a.end, a.scope, a.units, a.wide,
        agro_cols=not a.no_agro, gdd_bases=tuple(float(b) for b in a.gdd_base.split(",")),
        chill_start=a.chill_start, gdd_start=a.gdd_start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
