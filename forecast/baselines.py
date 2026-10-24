"""Score simple 7-day chill/GDD baselines on the uploaded CIMIS hourly data.

Target: for an issue date t, the total over days t+1..t+7 of
  chill_hours (32-45F), chill_portions (Dynamic model), gdd (base 50F).

Baselines
  persistence   total over the 7 days up to and including t
  climatology   mean target for the same day of year (+-3 days) in training seasons
  idw_*         same two, but built only from the *other* stations, weighted by
                1/distance^2: what an unsensed site would get (leave-one-station-out)

Test period is the last year (issue dates from 2025-10-23); climatology only
uses earlier years. Chill is scored on issue dates Nov-Feb, GDD on Mar-Oct.

Usage: python baselines.py [hourly_csv] [stations_csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cimis_puller"))
import agro  # noqa: E402

HERE = Path(__file__).resolve().parent
TEST_START = pd.Timestamp("2025-10-23")
TARGETS = ["chill_hours", "chill_portions", "gdd"]
MIN_HOURS = 20  # a day with fewer valid hourly temps is treated as missing


def load_hourly(hourly_csv: Path) -> pd.DataFrame:
    """Hourly station, timestamp_pst, date, temp_f with QC-rejected readings masked."""
    h = pd.read_csv(hourly_csv, usecols=["station", "timestamp_pst", "hly-air-tmp", "hly-air-tmp_qc"],
                    parse_dates=["timestamp_pst"])
    # CIMIS "R" = far outside the expected range; treat as missing. "Y" (moderate) is kept.
    temp_c = h["hly-air-tmp"].where(h["hly-air-tmp_qc"] != "R")
    h["temp_f"] = agro.c_to_f(temp_c)
    # hour 2400 is stamped as the next day's 00:00; shift back so it belongs to its own day
    h["date"] = (h["timestamp_pst"] - pd.Timedelta(minutes=1)).dt.normalize()
    return h.sort_values(["station", "timestamp_pst"])[["station", "timestamp_pst", "date", "temp_f"]]


def load_daily(hourly_csv: Path) -> pd.DataFrame:
    """One row per station-day with chill hours, chill portions and GDD."""
    return daily_from_hourly(load_hourly(hourly_csv))


def daily_from_hourly(h: pd.DataFrame) -> pd.DataFrame:
    """Daily chill hours, chill portions and GDD from hourly station/date/temp_f rows."""
    h = h.sort_values(["station", "timestamp_pst"])
    parts = []
    for st, g in h.groupby("station"):
        g = g.copy()
        g["ch"] = agro.chill_hours(g["temp_f"])
        reset = agro.season_id(g["date"], "11-01").diff().fillna(0).ne(0)
        g["cp"] = agro.dynamic_chill_portions(g["temp_f"], reset)
        d = g.groupby("date").agg(n=("temp_f", "count"), tmax=("temp_f", "max"), tmin=("temp_f", "min"),
                                  chill_hours=("ch", "sum"), chill_portions=("cp", "sum"))
        d["gdd"] = agro.gdd(d["tmax"], d["tmin"])
        d.loc[d["n"] < MIN_HOURS, TARGETS] = np.nan
        d["station"] = st
        parts.append(d.reset_index())
    return pd.concat(parts, ignore_index=True)


def add_windows(daily: pd.DataFrame) -> pd.DataFrame:
    """Add next-7-day targets (y_*) and past-7-day persistence (pers_*) per station."""
    out = []
    for _, g in daily.groupby("station"):
        g = g.set_index("date").asfreq("D")
        g["station"] = g["station"].ffill().bfill()
        for c in TARGETS:
            past = g[c].rolling(7, min_periods=7).sum()
            g[f"pers_{c}"] = past
            g[f"y_{c}"] = past.shift(-7)
        out.append(g.reset_index())
    return pd.concat(out, ignore_index=True)


def add_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """Mean next-7-day total for the same day of year (+-3 days), training years only."""
    df["doy"] = df["date"].dt.dayofyear.clip(upper=365)
    train = df[df["date"] < TEST_START - pd.Timedelta(days=7)]
    for c in TARGETS:
        by_doy = train.groupby(["station", "doy"])[f"y_{c}"].mean().unstack("doy")
        by_doy = by_doy.reindex(columns=range(1, 366))
        # circular +-3 day smoothing
        wrapped = pd.concat([by_doy.iloc[:, -3:], by_doy, by_doy.iloc[:, :3]], axis=1)
        smooth = wrapped.T.rolling(7, center=True, min_periods=1).mean().T.iloc[:, 3:-3]
        smooth.columns = range(1, 366)
        clim = smooth.stack().rename(f"clim_{c}").reset_index()
        clim.columns = ["station", "doy", f"clim_{c}"]
        df = df.merge(clim, on=["station", "doy"], how="left")
    return df


def haversine_km(lat1, lon1, lat2, lon2):
    p = np.radians
    a = np.sin(p(lat2 - lat1) / 2) ** 2 + np.cos(p(lat1)) * np.cos(p(lat2)) * np.sin(p(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def add_idw(df: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Leave-one-station-out versions of the baselines: inverse-distance^2 mix of the other stations."""
    loc = stations.set_index("station")[["latitude", "longitude"]]
    ids = list(loc.index)
    for base in ["pers", "clim"]:
        for c in TARGETS:
            wide = df.pivot(index="date", columns="station", values=f"{base}_{c}")
            est = {}
            for s in ids:
                others = [o for o in ids if o != s]
                w = np.array([1 / haversine_km(*loc.loc[s], *loc.loc[o]) ** 2 for o in others])
                vals = wide[others]
                wmat = vals.notna() * w
                est[s] = (vals.fillna(0) * w).sum(axis=1) / wmat.sum(axis=1).replace(0, np.nan)
            long = pd.DataFrame(est).stack().rename(f"idw_{base}_{c}").reset_index()
            long.columns = ["date", "station", f"idw_{base}_{c}"]
            df = df.merge(long, on=["date", "station"], how="left")
    return df


def score(df: pd.DataFrame, names: dict[str, str]) -> pd.DataFrame:
    test = df[(df["date"] >= TEST_START)]
    rows = []
    for c, months in [("chill_hours", [11, 12, 1, 2]), ("chill_portions", [11, 12, 1, 2]),
                      ("gdd", list(range(3, 11)))]:
        t = test[test["date"].dt.month.isin(months)]
        for st, g in list(t.groupby("station")) + [("all", t)]:
            row = {"target": c, "station": st, "n": int(g[f"y_{c}"].notna().sum()),
                   "mean_target": g[f"y_{c}"].mean()}
            for label, prefix in names.items():
                m = g[[f"y_{c}", f"{prefix}_{c}"]].dropna()
                row[f"mae_{label}"] = (m.iloc[:, 0] - m.iloc[:, 1]).abs().mean()
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    hourly = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data/cimis_hourly_2021-10-23_2026-10-22.csv"
    st_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "data/cimis_stations_selected.csv"
    stations = pd.read_csv(st_csv)

    daily = load_daily(hourly)
    daily.to_csv(HERE / "data/daily_station.csv", index=False)
    df = add_idw(add_climatology(add_windows(daily)), stations)

    names = {"persistence": "pers", "climatology": "clim",
             "loso_idw_persistence": "idw_pers", "loso_idw_climatology": "idw_clim"}
    res = score(df, names)
    res.to_csv(HERE / "baseline_scores.csv", index=False)
    pd.set_option("display.width", 200)
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
