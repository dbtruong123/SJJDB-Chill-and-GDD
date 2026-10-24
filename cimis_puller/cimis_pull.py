"""Pull CIMIS weather station data sequentially, one station at a time,
for a given year and season.

Usage:
    export CIMIS_APP_KEY=your-key
    python cimis_pull.py --year 2023 --season winter
    python cimis_pull.py --year 2023 --season summer --stations 2,6,80 --scope hourly
    python cimis_pull.py --year 2023 --months 3,4 --out data/

The app key is read from CIMIS_APP_KEY (or --app-key). Never commit it.
API docs: https://et.water.ca.gov/Rest/Index
"""
from __future__ import annotations

import argparse
import calendar
import csv
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

BASE_URL = "https://et.water.ca.gov"
# Current app keys go in this header; the old /api/data?appKey=... form is firewalled.
KEY_HEADER = "Ocp-Apim-Subscription-Key"

# Seasons are lists of (year_offset, month). Offset -1 means "previous calendar
# year", so winter 2023 = Dec 2022, Jan 2023, Feb 2023 (meteorological
# convention: the season is named by the year its January/February fall in).
SEASONS: dict[str, list[tuple[int, int]]] = {
    "winter": [(-1, 12), (0, 1), (0, 2)],
    "spring": [(0, 3), (0, 4), (0, 5)],
    "summer": [(0, 6), (0, 7), (0, 8)],
    "fall": [(0, 9), (0, 10), (0, 11)],
    "year": [(0, m) for m in range(1, 13)],
}

DAILY_ITEMS = [
    "day-air-tmp-avg", "day-air-tmp-max", "day-air-tmp-min",
    "day-rel-hum-avg", "day-rel-hum-max", "day-rel-hum-min",
    "day-dew-pnt", "day-vap-pres-avg",
    "day-wind-spd-avg", "day-wind-run",
    "day-sol-rad-avg", "day-soil-tmp-avg",
    "day-precip", "day-eto", "day-asce-eto",
]
HOURLY_ITEMS = [
    "hly-air-tmp", "hly-rel-hum", "hly-dew-pnt", "hly-vap-pres",
    "hly-wind-spd", "hly-wind-dir", "hly-res-wind",
    "hly-sol-rad", "hly-net-rad", "hly-soil-tmp",
    "hly-precip", "hly-eto", "hly-asce-eto",
]

# CIMIS caps a single request by records (one record = one station-day, or one
# station-hour for hourly data); hourly tops out at 5,020. Requests are chunked
# well under that.
MAX_RECORDS = 1750


@dataclass
class Station:
    number: int
    name: str
    city: str
    active: bool
    eto_station: bool
    elevation_ft: float | None
    latitude: float | None
    longitude: float | None
    connect_date: date | None
    disconnect_date: date | None

    def operating_during(self, start: date, end: date) -> bool:
        if self.connect_date and self.connect_date > end:
            return False
        if self.disconnect_date and self.disconnect_date < start:
            return False
        return True


def season_range(year: int, season: str | None = None,
                 months: list[int] | None = None) -> tuple[date, date]:
    """Return (start, end) inclusive dates for a season or explicit month list.

    Explicit months must be contiguous within the calendar year; use a named
    season for ranges that wrap around the new year.
    """
    if months:
        spec = [(0, m) for m in sorted(months)]
        if any(b - a != 1 for (_, a), (_, b) in zip(spec, spec[1:])):
            raise ValueError(f"months must be contiguous, got {months}")
    elif season:
        if season not in SEASONS:
            raise ValueError(f"unknown season {season!r}; choose from {sorted(SEASONS)}")
        spec = SEASONS[season]
    else:
        raise ValueError("give a season or a list of months")
    (y0, m0), (y1, m1) = spec[0], spec[-1]
    start = date(year + y0, m0, 1)
    end = date(year + y1, m1, calendar.monthrange(year + y1, m1)[1])
    return start, end


def _parse_mdY(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def _parse_coord(s: str | None) -> float | None:
    # CIMIS gives e.g. "36º20'10N / 36.336222"; the decimal part follows the slash.
    if not s or "/" not in s:
        return None
    try:
        return float(s.split("/")[-1].strip())
    except ValueError:
        return None


def _to_float(s) -> float | None:
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_stations(payload: dict | list) -> list[Station]:
    rows = payload.get("Stations") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError(f"unrecognised CIMIS station list: {str(payload)[:200]}")
    out = []
    for s in rows:
        out.append(Station(
            number=int(s["StationNbr"]),
            name=s.get("Name", ""),
            city=s.get("City", ""),
            active=str(s.get("IsActive", "")).lower() == "true",
            eto_station=str(s.get("IsEtoStation", "")).lower() == "true",
            elevation_ft=_to_float(s.get("Elevation")),
            latitude=_parse_coord(s.get("HmsLatitude")),
            longitude=_parse_coord(s.get("HmsLongitude")),
            connect_date=_parse_mdY(s.get("ConnectDate")),
            disconnect_date=_parse_mdY(s.get("DisconnectDate")),
        ))
    return sorted(out, key=lambda st: st.number)


def _snake(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def flatten_records(payload: dict) -> list[dict]:
    """Flatten CIMIS data JSON into one row per station-day (or station-hour).

    Each measurement becomes three columns: value, QC flag, and unit, e.g.
    day_air_tmp_avg, day_air_tmp_avg_qc, day_air_tmp_avg_unit. QC flags are
    kept because they are CIMIS's own validity markers (useful ground truth
    for faulty-sensor detection).
    """
    rows = []
    providers = (payload.get("Data") or {}).get("Providers") or []
    for prov in providers:
        for rec in prov.get("Records") or []:
            row = {}
            for key, val in rec.items():
                if isinstance(val, dict):
                    col = _snake(key)
                    row[col] = _to_float(val.get("Value"))
                    row[f"{col}_qc"] = (val.get("Qc") or "").strip()
                    row[f"{col}_unit"] = val.get("Unit")
                else:
                    row[_snake(key)] = val
            rows.append(row)
    return rows


def date_chunks(start: date, end: date, records_per_day: int) -> list[tuple[date, date]]:
    days_per_chunk = max(1, MAX_RECORDS // records_per_day)
    chunks, cur = [], start
    while cur <= end:
        stop = min(end, cur + timedelta(days=days_per_chunk - 1))
        chunks.append((cur, stop))
        cur = stop + timedelta(days=1)
    return chunks


def _json_or_explain(resp: requests.Response):
    """CIMIS's firewall answers some requests with an HTML "Request Rejected" page and status 200."""
    try:
        return resp.json()
    except ValueError:
        text = " ".join(resp.text.split())[:200]
        hint = (" This is CIMIS's firewall page: the request went to an address it blocks, "
                "e.g. the old /api/data?appKey=... form." if "rejected" in text.lower() else "")
        raise RuntimeError(f"CIMIS sent a non-JSON reply from {resp.url.split('?')[0]}: {text!r}.{hint}") from None


class CimisClient:
    def __init__(self, app_key: str, pause: float = 1.0, retries: int = 4,
                 timeout: float = 60.0, session: requests.Session | None = None):
        self.app_key = app_key
        self.pause = pause
        self.retries = retries
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"Accept": "application/json", KEY_HEADER: app_key})

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{BASE_URL}/{path}"
        delay = 2.0
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return _json_or_explain(resp)
                # 4xx other than rate limiting means a bad request or bad key; don't retry.
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    raise RuntimeError(f"CIMIS {resp.status_code}: {resp.text[:300]}")
                err = f"HTTP {resp.status_code}"
            except (requests.ConnectionError, requests.Timeout) as e:
                err = str(e)
            if attempt == self.retries:
                raise RuntimeError(f"CIMIS request failed after {self.retries + 1} tries: {err}")
            time.sleep(delay)
            delay *= 2
        raise AssertionError("unreachable")

    def stations(self) -> list[Station]:
        return parse_stations(self._get("StationWeb/GetAllStations"))

    def data(self, station: int, start: date, end: date, items: list[str],
             unit: str = "M") -> list[dict]:
        params = {
            "stationNbrs": str(station),
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "isHourly": str(items[0].startswith("hly-")).lower(),
            "dataItems": ",".join(items),
            "unitOfMeasure": unit,
        }
        payload = self._get("StationWeb/GetDataByStationNumber", params)
        time.sleep(self.pause)
        return flatten_records(payload)


def write_csv(path: Path, rows: list[dict]) -> None:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    tmp = path.with_suffix(".csv.part")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def write_stations(path: Path, stations: list[Station]) -> None:
    rows = [{k: (v.isoformat() if isinstance(v, date) else v)
             for k, v in vars(s).items()} for s in stations]
    write_csv(path, rows)


def pull(client: CimisClient, year: int, season: str | None, months: list[int] | None,
         out_dir: Path, scope: str = "daily", station_filter: list[int] | None = None,
         include_inactive: bool = True, unit: str = "M", overwrite: bool = False,
         log=print) -> Path:
    start, end = season_range(year, season, months)
    label = season or "m" + "-".join(str(m) for m in sorted(months or []))
    run_dir = out_dir / f"{year}_{label}_{scope}"
    run_dir.mkdir(parents=True, exist_ok=True)

    stations = client.stations()
    write_stations(run_dir / "stations.csv", stations)
    targets = [s for s in stations if s.operating_during(start, end)]
    if not include_inactive:
        targets = [s for s in targets if s.active]
    if station_filter:
        wanted = set(station_filter)
        targets = [s for s in targets if s.number in wanted]

    items = DAILY_ITEMS if scope == "daily" else HOURLY_ITEMS
    per_day = 1 if scope == "daily" else 24
    chunks = date_chunks(start, end, per_day)
    log(f"{start} to {end}: {len(targets)} stations, {len(chunks)} request(s) each -> {run_dir}")

    failures = []
    for i, st in enumerate(targets, 1):
        dest = run_dir / f"station_{st.number:03d}.csv"
        if dest.exists() and not overwrite:
            log(f"[{i}/{len(targets)}] station {st.number} {st.name}: already pulled, skipping")
            continue
        try:
            rows = []
            for a, b in chunks:
                rows.extend(client.data(st.number, a, b, items, unit))
        except RuntimeError as e:
            log(f"[{i}/{len(targets)}] station {st.number} {st.name}: FAILED ({e})")
            failures.append((st.number, str(e)))
            continue
        if rows:
            write_csv(dest, rows)
        log(f"[{i}/{len(targets)}] station {st.number} {st.name}: {len(rows)} rows")

    if failures:
        with (run_dir / "failures.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["station", "error"])
            w.writerows(failures)
        log(f"{len(failures)} station(s) failed; see failures.csv. Re-run to retry them.")
    return run_dir


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--year", type=int, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--season", choices=sorted(SEASONS))
    g.add_argument("--months", help="contiguous months, e.g. 3,4,5")
    p.add_argument("--scope", choices=["daily", "hourly"], default="daily")
    p.add_argument("--stations", help="comma-separated station numbers (default: all operating)")
    p.add_argument("--active-only", action="store_true", help="skip stations CIMIS marks inactive today")
    p.add_argument("--units", choices=["M", "E"], default="M", help="M=metric, E=English")
    p.add_argument("--out", type=Path, default=Path("data/cimis"))
    p.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--app-key", default=os.environ.get("CIMIS_APP_KEY"))
    a = p.parse_args(argv)

    if not a.app_key:
        p.error("set CIMIS_APP_KEY or pass --app-key (get one at https://et.water.ca.gov)")
    months = [int(m) for m in a.months.split(",")] if a.months else None
    stations = [int(s) for s in a.stations.split(",")] if a.stations else None

    pull(CimisClient(a.app_key, pause=a.pause), a.year, a.season, months, a.out,
         scope=a.scope, station_filter=stations, include_inactive=not a.active_only,
         unit=a.units, overwrite=a.overwrite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
