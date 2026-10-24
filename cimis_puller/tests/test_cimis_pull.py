import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cimis_pull as cp

STATIONS = {"Stations": [
    {"StationNbr": "2", "Name": "FivePoints", "City": "Five Points", "IsActive": "True",
     "IsEtoStation": "True", "Elevation": "285", "HmsLatitude": "36º20'10N / 36.336222",
     "HmsLongitude": "-120º6'46W / -120.112910", "ConnectDate": "6/7/1982", "DisconnectDate": "12/31/2050"},
    {"StationNbr": "1", "Name": "Old", "City": "X", "IsActive": "False", "IsEtoStation": "False",
     "Elevation": "10", "HmsLatitude": "", "HmsLongitude": "", "ConnectDate": "1/1/1982", "DisconnectDate": "1/1/1990"},
]}

def data_payload(station, start, end):
    recs, d = [], start
    while d <= end:
        recs.append({"Date": d.isoformat(), "Julian": "1", "Station": str(station), "Scope": "daily",
                     "DayAirTmpAvg": {"Value": "7.5", "Qc": " ", "Unit": "(C)"},
                     "DayPrecip": {"Value": None, "Qc": "M", "Unit": "(mm)"}})
        d = date.fromordinal(d.toordinal() + 1)
    return {"Data": {"Providers": [{"Name": "cimis", "Records": recs}]}}

class FakeClient(cp.CimisClient):
    def __init__(self):
        self.calls = []
    def stations(self):
        return cp.parse_stations(STATIONS)
    def data(self, station, start, end, items, unit="M"):
        self.calls.append((station, start, end))
        return cp.flatten_records(data_payload(station, start, end))

def test_winter_wraps_year():
    assert cp.season_range(2023, "winter") == (date(2022, 12, 1), date(2023, 2, 28))
    assert cp.season_range(2024, "winter") == (date(2023, 12, 1), date(2024, 2, 29))
    assert cp.season_range(2023, "summer") == (date(2023, 6, 1), date(2023, 8, 31))
    assert cp.season_range(2023, months=[4, 3]) == (date(2023, 3, 1), date(2023, 4, 30))

def test_noncontiguous_months_rejected():
    import pytest
    with pytest.raises(ValueError):
        cp.season_range(2023, months=[1, 3])

def test_chunks_respect_record_cap():
    ch = cp.date_chunks(date(2023, 6, 1), date(2023, 8, 31), 24)
    assert all(((b - a).days + 1) * 24 <= cp.MAX_RECORDS for a, b in ch)
    assert ch[0][0] == date(2023, 6, 1) and ch[-1][1] == date(2023, 8, 31)

def test_parse_stations():
    st = cp.parse_stations(STATIONS)
    assert [s.number for s in st] == [1, 2]
    assert abs(st[1].latitude - 36.336222) < 1e-9 and st[0].latitude is None

def test_flatten_keeps_qc():
    row = cp.flatten_records(data_payload(2, date(2023, 1, 1), date(2023, 1, 1)))[0]
    assert row["day_air_tmp_avg"] == 7.5 and row["day_air_tmp_avg_unit"] == "(C)"
    assert row["day_precip"] is None and row["day_precip_qc"] == "M"

def test_pull_sequential_and_resume(tmp_path):
    c = FakeClient()
    run = cp.pull(c, 2023, "winter", None, tmp_path, log=lambda *_: None)
    assert (run / "station_002.csv").exists()
    assert not (run / "station_001.csv").exists()  # disconnected in 1990
    assert {s for s, *_ in c.calls} == {2}
    assert len((run / "station_002.csv").read_text().splitlines()) == 1 + 90
    c2 = FakeClient()
    cp.pull(c2, 2023, "winter", None, tmp_path, log=lambda *_: None)
    assert c2.calls == []  # already pulled, skipped
