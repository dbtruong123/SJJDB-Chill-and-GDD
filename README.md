# Chill and GDD forecasting for Central Valley orchards

Answers three grower questions for five CIMIS stations (6 Davis, 70 Manteca, 71 Modesto,
39 Parlier, 5 Shafter): how much chill and heat has accumulated this season, how that
compares to past years, and what to expect over the next 7 days.

- **Chill hours**: hours between 32 and 45 F
- **Chill portions**: Dynamic model (UC Davis FNRIC)
- **GDD**: simple average method, base 50 F
- Chill seasons reset on Nov 1, GDD on Jan 1

## Layout

| Path | What it does |
| --- | --- |
| `cimis_puller/agro.py` | Chill hours, Utah units, chill portions and GDD from hourly temperatures |
| `cimis_puller/cimis_pull.py` | CIMIS Web API client |
| `cimis_puller/pipeline.py` | Builds an ML-ready station dataset from the API |
| `forecast/daily_forecast.py` | Daily 7-day forecast: `pull`, `train`, `predict`, `live` |
| `forecast/api.py` | HTTP API for the frontend (see `forecast/API.md`) |
| `forecast/baselines.py` | Daily totals, persistence and climatology baselines (used by the forecaster) |
| `forecast/map_loso.py` | Leave-one-station-out test for filling the map between stations |
| `forecast/dashboard_data.py` | Builds the dashboard's files: daily history + forecast, stations, map grid with kriging weights |
| `forecast/forecast_pull.py` | Optional: archived weather-model forecasts from Open-Meteo |

## Setup

```
pip install -r requirements.txt
```

The forecaster reads the hourly CIMIS export from `data/cimis_hourly_2021-10-23_2026-10-22.csv`
(or `forecast/data/`, or any file passed with `--hourly`). Columns used: `station`, `timestamp_pst`,
`hly-air-tmp` (C), `hly-air-tmp_qc`. `live` calls CIMIS's `StationWeb/GetDataByStationNumber`
with the app key in the `Ocp-Apim-Subscription-Key` header.

## Run

```
cd forecast
export CIMIS_APP_KEY=...           # never commit this
python daily_forecast.py pull      # optional: rebuild data/cimis_hourly_<start>_<end>.csv from the API (5 years)
python daily_forecast.py train     # scores the last year, then refits on all years and saves models/
python daily_forecast.py predict   # writes forecast_output.csv for the last day in the data
python daily_forecast.py live      # pulls the last 3 weeks from CIMIS and re-forecasts
python dashboard_data.py           # refreshes dashboard/daily.csv, stations.csv, map_grid.csv
```

`forecast_output.csv` has one row per station and forecast day: daily chill hours, chill
portions and GDD, plus season-to-date totals including the forecast days.

## API for the frontend

```
cd forecast
export CIMIS_APP_KEY=...           # optional: pulls fresh readings at start-up and every 6 hours
uvicorn api:app --port 8000        # needs the trained model; docs at http://127.0.0.1:8000/docs
```

Endpoints and example responses: `forecast/API.md`.

## Method

For each quantity and each lead day (1 to 7), a gradient-boosting model shared by all five
stations predicts the departure from that station's normal, using the last week of readings,
recent temperature trend, the other stations' readings, season timing and location. Each
day's forecast blends that model with persistence (today's value) and climatology, with blend
weights chosen on held-out seasons. Near-term days lean on recent readings; later days lean
on normals.

## Results (test year Oct 2025 to Oct 2026, mean absolute error per day)

| | Day 1 | Day 3 | Day 7 |
| --- | --- | --- | --- |
| GDD (Mar-Oct) | 2.2 (best baseline 2.4) | 4.1 (4.5) | 4.6 (4.6) |
| Chill portions (Nov-Feb) | 0.26 (0.42) | 0.37 (0.39) | 0.40 (0.42) |
| Chill hours (Nov-Feb) | 2.9 (2.8) | 5.2 (4.7) | 6.1 (6.1) |

Full tables: `forecast/daily_forecast_scores.csv`, `forecast/baseline_scores.csv`,
`forecast/map_loso_scores.csv`.
