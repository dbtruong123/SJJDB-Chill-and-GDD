import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agro
import cimis_pull as cp
import pipeline as pl

GAP = date(2022, 3, 15)  # pretend CIMIS returned nothing for this day
NUMS = pl.DEFAULT_STATIONS
STATIONS = {"Stations": [
    {"StationNbr": str(n), "Name": f"S{n}", "City": "", "IsActive": "True", "IsEtoStation": "True",
     "Elevation": "100", "HmsLatitude": f"x / {36 + i * 0.5}", "HmsLongitude": f"x / {-120 - i * 0.5}",
     "ConnectDate": "1/1/2000", "DisconnectDate": "12/31/2050"} for i, n in enumerate(NUMS)]}


def winter(d):
    return d.month in (12, 1)


class FakeClient(cp.CimisClient):
    """Daily: 20C max / 10C min (GDD base 50F = 9). Hourly: 40F in Dec-Jan, 70F otherwise."""
    def __init__(self):
        self.calls = []
    def stations(self):
        return cp.parse_stations(STATIONS)
    def data(self, station, start, end, items, unit="M"):
        hourly = items[0].startswith("hly")
        self.calls.append((station, "h" if hourly else "d", start, end))
        recs, d = [], start
        while d <= end:
            if d != GAP:
                if hourly:
                    for h in range(100, 2500, 100):
                        qc = "Y" if (station == 70 and d == date(2022, 1, 2) and h == 100) else " "
                        recs.append({"Date": d.isoformat(), "Hour": f"{h:04d}", "Station": str(station),
                                     "HlyAirTmp": {"Value": "40" if winter(d) else "70", "Qc": qc, "Unit": "(F)"}})
                else:
                    qc = "R" if (station == 71 and d == date(2022, 1, 1)) else " "
                    recs.append({"Date": d.isoformat(), "Station": str(station),
                                 "DayAirTmpMax": {"Value": "20", "Qc": qc, "Unit": "(C)"},
                                 "DayAirTmpMin": {"Value": "10", "Qc": " ", "Unit": "(C)"}})
            d += timedelta(days=1)
        return cp.flatten_records({"Data": {"Providers": [{"Records": recs}]}})


QUIET = dict(log=lambda *_: None)


@pytest.fixture(scope="module")
def full(tmp_path_factory):
    c = FakeClient()
    out = pl.run(c, tmp_path_factory.mktemp("o") / "o.csv", **QUIET)
    df = pd.read_csv(out, parse_dates=["timestamp"], keep_default_na=False, na_values=[""])
    return c, out, df


def row(df, st, day):
    return df[(df.station == st) & (df.timestamp == day)].iloc[0]


def test_default_five_stations_pulled_in_order(full):
    c, _, df = full
    days = (pl.DEFAULT_END - pl.DEFAULT_START).days + 1
    assert len(df) == 5 * days and list(df.station.unique()) == sorted(NUMS)
    order = [s for s, *_ in c.calls]
    assert order == sorted(order, key=NUMS.index)  # one station at a time, in the given order


def test_gaps_and_qc(full):
    _, out, df = full
    assert df.record_missing.sum() == 5
    r = row(df, 71, "2022-01-01")
    assert r.day_air_tmp_max_qc == "R" and r.day_air_tmp_max_flag == 1
    g = row(df, 6, str(GAP))
    assert g.hourly_temp_count == 0 and pd.isna(g.chill_hours) and pd.isna(g.gdd_b50)
    assert row(df, 70, "2022-01-02").hourly_temp_flagged == 1
    units = json.loads(out.with_name("o_units.json").read_text())["units"]
    assert units["day_air_tmp_max"] == "(C)"


def test_chill_and_gdd(full):
    _, _, df = full
    jan = row(df, 6, "2022-01-10")
    assert jan.chill_hours == 24 and jan.chill_units_utah == 12 and jan.hourly_temp_count == 24
    assert 0 < jan.chill_portions < 2
    summer = row(df, 6, "2022-07-10")
    assert summer.chill_hours == 0 and summer.chill_units_utah == -12 and summer.chill_portions == 0
    assert jan.gdd_b50 == pytest.approx(9.0)
    # chill season resets Nov 1: Dec 1 2021 starts at 0 and accumulates 31*24 by Dec 31
    assert row(df, 6, "2021-12-31").chill_hours_cum == 31 * 24
    assert row(df, 6, "2022-11-01").chill_hours_cum == 0 and row(df, 6, "2022-11-01").chill_season == 2022
    # GDD resets Jan 1
    assert row(df, 6, "2022-01-01").gdd_b50_cum == pytest.approx(9.0)
    assert row(df, 6, "2022-01-03").gdd_b50_cum == pytest.approx(27.0)


def test_wide_and_multiple_bases(tmp_path):
    out = pl.run(FakeClient(), tmp_path / "w.csv", start=date(2022, 1, 1), end=date(2022, 1, 3),
                 wide=True, gdd_bases=(45.0, 50.0), **QUIET)
    df = pd.read_csv(out)
    assert len(df) == 3
    assert {f"s{n}_chill_hours" for n in NUMS} <= set(df.columns)
    assert df.loc[0, "s6_gdd_b45"] == pytest.approx(14.0)


def test_hourly_scope_and_nearest(tmp_path):
    out = pl.run(FakeClient(), tmp_path / "h.csv", lat=36.05, lon=-119.95,
                 start=date(2022, 3, 14), end=date(2022, 3, 16), scope="hourly", **QUIET)
    df = pd.read_csv(out)
    assert (df.station == 6).all()
    assert len(df) == 72 and df.record_missing.sum() == 24 and "chill_hours" not in df


def test_season_id():
    s = agro.season_id(pd.Series(pd.to_datetime(["2021-10-31", "2021-11-01", "2022-02-01"])), "11-01")
    assert s.tolist() == [2020, 2021, 2021]
