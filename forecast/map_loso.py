"""Leave-one-station-out test of how to fill the map between stations.

Question: should the map interpolate hourly *temperatures* and then compute chill/GDD
per location, or interpolate the chill/GDD *totals* directly? Chill is a threshold
(32-45F) so the two can differ.

For each held-out station s, the other four stations' observations are combined with
fixed spatial weights and compared with what s actually measured, as 7-day totals.
Weight schemes (all depend only on station geometry, so the same weights apply in
both spaces and any difference comes from the interpolation space alone):
  idw        inverse distance squared
  ok         ordinary kriging, linear variogram
  uk_elev    universal kriging, linear variogram, linear drift in elevation

Usage: python map_loso.py [hourly_csv] [stations_csv]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from baselines import HERE, TARGETS, add_windows, daily_from_hourly, haversine_km, load_hourly


def dist_matrix(loc: pd.DataFrame) -> np.ndarray:
    lat, lon = loc["latitude"].to_numpy(), loc["longitude"].to_numpy()
    return haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])


def kriging_weights(d_oo: np.ndarray, d_os: np.ndarray, drift_o=None, drift_s=None) -> np.ndarray:
    """Kriging weights with a linear variogram gamma(d) = d (its slope cancels out).

    Without drift this is ordinary kriging (weights sum to 1). drift_o (n x k) and
    drift_s (k,) add universal-kriging constraints sum(w * drift_o[:, j]) = drift_s[j].
    """
    n = len(d_os)
    f_o = np.ones((n, 1)) if drift_o is None else np.column_stack([np.ones(n), drift_o])
    f_s = np.ones(1) if drift_s is None else np.concatenate([[1.0], np.atleast_1d(drift_s)])
    k = f_o.shape[1]
    a = np.zeros((n + k, n + k))
    a[:n, :n] = d_oo
    a[:n, n:] = f_o
    a[n:, :n] = f_o.T
    b = np.concatenate([d_os, f_s])
    return np.linalg.solve(a, b)[:n]


def weight_schemes(stations: pd.DataFrame, held: int) -> dict[str, pd.Series]:
    loc = stations.set_index("station")
    others = [s for s in loc.index if s != held]
    d = dist_matrix(loc.loc[others + [held]])
    d_oo, d_os = d[:-1, :-1], d[:-1, -1]
    elev = loc["elevation_ft"]
    return {
        "idw": pd.Series(1 / d_os**2 / (1 / d_os**2).sum(), index=others),
        "ok": pd.Series(kriging_weights(d_oo, d_os), index=others),
        "uk_elev": pd.Series(kriging_weights(d_oo, d_os, elev.loc[others].to_numpy()[:, None],
                                             elev.loc[held]), index=others),
    }


def weighted(wide: pd.DataFrame, w: pd.Series) -> pd.Series:
    """Weighted combination of station columns; NaN when any contributing station is missing."""
    return wide[w.index].mul(w, axis=1).sum(axis=1, min_count=len(w)).where(wide[w.index].notna().all(axis=1))


def main():
    hourly_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data/cimis_hourly_2021-10-23_2026-10-22.csv"
    st_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "data/cimis_stations_selected.csv"
    stations = pd.read_csv(st_csv)

    hourly = load_hourly(hourly_csv)
    temps = hourly.pivot(index="timestamp_pst", columns="station", values="temp_f")
    observed = add_windows(daily_from_hourly(hourly))
    obs_wide = {c: observed.pivot(index="date", columns="station", values=f"y_{c}") for c in TARGETS}

    rows = []
    for held in stations["station"]:
        truth = observed[observed["station"] == held].set_index("date")
        for scheme, w in weight_schemes(stations, held).items():
            # temperature space: interpolate each hour, then compute chill/GDD at the held-out site
            est_h = weighted(temps, w).rename("temp_f").reset_index()
            est_h["station"] = held
            est_h["date"] = (est_h["timestamp_pst"] - pd.Timedelta(minutes=1)).dt.normalize()
            via_temp = add_windows(daily_from_hourly(est_h)).set_index("date")
            for c, months in [("chill_hours", [11, 12, 1, 2]), ("chill_portions", [11, 12, 1, 2]),
                              ("gdd", list(range(3, 11)))]:
                via_total = weighted(obs_wide[c], w)
                df = pd.DataFrame({"truth": truth[f"y_{c}"], "temp_space": via_temp[f"y_{c}"],
                                   "total_space": via_total}).dropna()
                df = df[df.index.month.isin(months)]
                rows.append({"target": c, "station": held, "scheme": scheme, "n": len(df),
                             "mean_target": df["truth"].mean(),
                             "mae_temp_space": (df["temp_space"] - df["truth"]).abs().mean(),
                             "mae_total_space": (df["total_space"] - df["truth"]).abs().mean(),
                             "bias_temp_space": (df["temp_space"] - df["truth"]).mean(),
                             "bias_total_space": (df["total_space"] - df["truth"]).mean()})
            print(f"station {held} {scheme}: weights {w.round(2).to_dict()}")

    res = pd.DataFrame(rows)
    res.to_csv(HERE / "map_loso_scores.csv", index=False)
    pd.set_option("display.width", 200)
    summary = res.groupby(["target", "scheme"])[["mae_temp_space", "mae_total_space"]].mean().round(2)
    print(summary.to_string())
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
