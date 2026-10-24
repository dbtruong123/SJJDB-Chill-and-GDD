"""API tests against the real hourly file and the saved model (skipped when either is missing)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import daily_forecast as dfc  # noqa: E402

if not (dfc.MODEL_PATH.exists() and dfc.DEFAULT_HOURLY.exists()):
    pytest.skip("needs the hourly CSV and a trained model (python daily_forecast.py train)",
                allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402


@pytest.fixture(scope="module")
def client(tmp_path_factory, monkeypatch_module):
    # keep refreshes away from the real data/live_hourly.csv
    monkeypatch_module.setattr(dfc, "LIVE_HOURLY", tmp_path_factory.mktemp("live") / "live_hourly.csv")
    monkeypatch_module.delenv("CIMIS_APP_KEY", raising=False)
    with TestClient(api.app) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_stations_and_health(client):
    st = client.get("/api/stations").json()
    assert sorted(s["station"] for s in st) == [5, 6, 39, 70, 71]
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["live_updates"] is False


def test_summary_matches_forecast_file(client):
    s = client.get("/api/stations/6/summary", params={"measure": "gdd"}).json()
    fc = client.get("/api/forecast", params={"station": 6}).json()
    assert len(fc) == 7 and [r["horizon"] for r in fc] == list(range(1, 8))
    assert s["season_to_date"] + fc[0]["gdd"] == pytest.approx(fc[0]["gdd_season_to_date"], abs=0.02)
    assert s["projected"] == pytest.approx(fc[-1]["gdd_season_to_date"], abs=0.02)
    assert s["next7"] == pytest.approx(sum(r["gdd"] for r in fc), abs=0.05)
    assert len(s["past_seasons_same_date"]) >= 3


def test_seasons_current_curve_ends_in_forecast(client):
    r = client.get("/api/stations/39/seasons", params={"measure": "chill_portions"}).json()
    cur = [s for s in r["seasons"] if s["current"]]
    assert len(cur) == 1 and cur[0]["points"][-1]["kind"] in ("forecast", "observed")
    totals = [p["total"] for p in cur[0]["points"]]
    assert totals == sorted(totals)  # running totals never fall


def test_point_on_a_station_equals_that_station(client):
    st = {s["station"]: s for s in client.get("/api/stations").json()}
    p = client.get("/api/point", params={"lat": st[71]["latitude"], "lon": st[71]["longitude"]}).json()
    s = client.get("/api/stations/71/summary").json()
    assert p["nearest_station"] == 71 and p["season_to_date"] == pytest.approx(s["season_to_date"], abs=0.02)


def test_map_points_are_weighted_station_values(client):
    m = client.get("/api/map", params={"measure": "gdd", "value": "next7"}).json()
    vals = [s["value"] for s in m["stations"]]
    assert len(m["points"]) > 1000
    assert all(min(vals) - 5 <= p["value"] <= max(vals) + 5 for p in m["points"])


def test_bad_input(client):
    assert client.get("/api/stations/99/summary").status_code == 404
    assert client.get("/api/map", params={"measure": "rain"}).status_code == 422
    assert client.post("/api/refresh").status_code == 400  # no key on the server


def test_refresh_moves_the_issue_date(client, monkeypatch):
    before = client.get("/api/health").json()["issue_date"]
    arch = pd.read_csv(dfc.DEFAULT_HOURLY, usecols=["station", "timestamp_pst", "hly-air-tmp", "hly-air-tmp_qc"],
                       parse_dates=["timestamp_pst"])
    last = arch[arch["timestamp_pst"] > arch["timestamp_pst"].max() - pd.Timedelta(days=1)]
    nxt = last.assign(timestamp_pst=last["timestamp_pst"] + pd.Timedelta(days=1))  # one more day of readings
    monkeypatch.setenv("CIMIS_APP_KEY", "test")
    monkeypatch.setattr(dfc, "fetch_live", lambda stations, days, key: nxt)
    h = client.post("/api/refresh").json()
    assert h["source"] == "CIMIS API" and h["issue_date"] > before

    def boom(*a, **k):
        raise RuntimeError("CIMIS sent a non-JSON reply")
    monkeypatch.setattr(dfc, "fetch_live", boom)
    r = client.post("/api/refresh")
    assert r.status_code == 502 and client.get("/api/health").json()["issue_date"] == h["issue_date"]
