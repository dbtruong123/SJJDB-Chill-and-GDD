"""Pull archived weather-model temperature forecasts for the CIMIS stations (run on your machine).

Uses Open-Meteo's Previous Model Runs API (https://open-meteo.com/en/docs/previous-runs-api):
`temperature_2m_previous_dayN` is the hourly temperature the model predicted N days
(N = 1..7) before that hour. GFS 2 m temperature goes back to March 2021, so it covers
the whole CIMIS window. No API key is needed.

Output: data/forecast_hourly.csv, long format
    station, timestamp_pst, lead_day, temp_f
Timestamps are fixed PST (UTC-8) like CIMIS, so the two line up hour for hour.

Usage:
    python forecast_pull.py                          # all stations in data/cimis_stations_selected.csv
    python forecast_pull.py --start 2021-10-23 --end 2026-10-22 --model gfs_seamless
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
LEADS = range(1, 8)


def year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    out, s = [], start
    while s <= end:
        e = min(date(s.year, 12, 31), end)
        out.append((s, e))
        s = e + timedelta(days=1)
    return out


def fetch(lat: float, lon: float, start: date, end: date, model: str, retries: int = 4) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "hourly": ",".join(f"temperature_2m_previous_day{n}" for n in LEADS),
        "models": model, "temperature_unit": "fahrenheit", "timezone": "Etc/GMT+8",
    }
    for attempt in range(retries):
        r = requests.get(URL, params=params, timeout=120)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            time.sleep(2 ** (attempt + 1))
            continue
        raise RuntimeError(f"Open-Meteo {r.status_code}: {r.text[:300]}")
    raise RuntimeError("unreachable")


def to_long(payload: dict, station: int) -> pd.DataFrame:
    """Turn one response into station/timestamp_pst/lead_day/temp_f rows."""
    hourly = payload["hourly"]
    wide = pd.DataFrame(hourly)
    wide["timestamp_pst"] = pd.to_datetime(wide.pop("time"))
    long = wide.melt(id_vars="timestamp_pst", var_name="var", value_name="temp_f")
    long["lead_day"] = long.pop("var").str.extract(r"previous_day(\d+)$", expand=False).astype(int)
    long["station"] = station
    return long[["station", "timestamp_pst", "lead_day", "temp_f"]]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stations", type=Path, default=HERE / "data/cimis_stations_selected.csv")
    ap.add_argument("--start", type=date.fromisoformat, default=date(2021, 10, 23))
    ap.add_argument("--end", type=date.fromisoformat, default=date(2026, 10, 22))
    ap.add_argument("--model", default="gfs_seamless", help="Open-Meteo model name (GFS covers back to 2021)")
    ap.add_argument("--out", type=Path, default=HERE / "data/forecast_hourly.csv")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args(argv)

    stations = pd.read_csv(args.stations)
    parts = []
    for _, st in stations.iterrows():
        for s, e in year_chunks(args.start, args.end):
            print(f"station {st['station']} {s}..{e}", file=sys.stderr)
            parts.append(to_long(fetch(st["latitude"], st["longitude"], s, e, args.model), int(st["station"])))
            time.sleep(args.pause)
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(args.out, index=False)
    missing = out["temp_f"].isna().mean()
    print(f"wrote {len(out):,} rows to {args.out} ({missing:.1%} missing)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
