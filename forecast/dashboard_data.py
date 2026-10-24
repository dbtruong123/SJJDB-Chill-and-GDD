"""Build the three files the grower dashboard reads.

  dashboard/daily.csv     station, date, kind (observed|forecast), chill_hours, chill_portions, gdd
  dashboard/stations.csv  station, name, latitude, longitude, elevation_ft
  dashboard/map_grid.csv  grid points along the valley between the stations, with the
                          ordinary-kriging weight of each station (w_<id>) and the distance
                          to the nearest station; any station value maps to a point as
                          sum(w_i * value_i), so the page can draw any day or season total

Run after `daily_forecast.py predict` so the forecast rows are current.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from baselines import HERE, haversine_km
from map_loso import dist_matrix, kriging_weights

OUT = HERE / "dashboard"
STEP_DEG = 0.05      # about 5 km
CORRIDOR_KM = 35     # keep points this close to the line through the stations (the valley floor)


def corridor_grid(stations: pd.DataFrame) -> pd.DataFrame:
    s = stations.sort_values("latitude", ascending=False)
    lat = np.arange(s["latitude"].min() - 0.3, s["latitude"].max() + 0.3, STEP_DEG)
    lon = np.arange(s["longitude"].min() - 0.4, s["longitude"].max() + 0.4, STEP_DEG)
    g = pd.DataFrame([(a, b) for a in lat for b in lon], columns=["latitude", "longitude"])
    # distance to each segment of the north-to-south station line, on a local flat projection
    kx = 111.32 * np.cos(np.radians(s["latitude"].mean()))
    p = np.column_stack([g["longitude"] * kx, g["latitude"] * 110.57])
    v = np.column_stack([s["longitude"] * kx, s["latitude"] * 110.57])
    d = np.full(len(g), np.inf)
    for a, b in zip(v[:-1], v[1:]):
        t = np.clip(((p - a) @ (b - a)) / ((b - a) @ (b - a)), 0, 1)
        d = np.minimum(d, np.linalg.norm(p - (a + t[:, None] * (b - a)), axis=1))
    return g[d <= CORRIDOR_KM].reset_index(drop=True)


def weights(grid: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    ids = stations["station"].tolist()
    d_oo = dist_matrix(stations)
    lat, lon = stations["latitude"].to_numpy(), stations["longitude"].to_numpy()
    rows = []
    for _, pt in grid.iterrows():
        d_os = haversine_km(pt["latitude"], pt["longitude"], lat, lon)
        if d_os.min() < 0.5:  # on top of a station: that station's value exactly
            w = (d_os == d_os.min()).astype(float)
        else:
            w = kriging_weights(d_oo, d_os)
        rows.append({"latitude": round(pt["latitude"], 3), "longitude": round(pt["longitude"], 3),
                     "nearest_km": round(float(d_os.min()), 1),
                     **{f"w_{i}": round(float(x), 4) for i, x in zip(ids, w)}})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    stations = pd.read_csv(HERE / "data/cimis_stations_selected.csv")
    stations = stations[["station", "name", "latitude", "longitude", "elevation_ft"]].sort_values("station")
    stations.to_csv(OUT / "stations.csv", index=False)

    obs = pd.read_csv(HERE / "data/daily_station.csv", parse_dates=["date"])
    obs = obs[["station", "date", "chill_hours", "chill_portions", "gdd"]].assign(kind="observed")
    fc = pd.read_csv(HERE / "forecast_output.csv", parse_dates=["target_date"])
    fc = fc.rename(columns={"target_date": "date"})[["station", "date", "chill_hours", "chill_portions", "gdd"]]
    fc = fc.assign(kind="forecast")
    daily = pd.concat([obs, fc]).sort_values(["station", "date"])
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    daily[["station", "date", "kind", "chill_hours", "chill_portions", "gdd"]].to_csv(
        OUT / "daily.csv", index=False, float_format="%.2f")

    grid = weights(corridor_grid(stations), stations)
    grid.to_csv(OUT / "map_grid.csv", index=False)
    print(f"{len(daily):,} daily rows, {len(grid):,} map points")


if __name__ == "__main__":
    main()
