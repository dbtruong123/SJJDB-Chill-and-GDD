# Chill & GDD API

Base URL when run locally: `http://127.0.0.1:8000`. Interactive docs (try every call in the browser): `/docs`.
All responses are JSON. CORS is open, so a frontend on any port can call it.

`measure` is one of `gdd`, `chill_portions`, `chill_hours` (default `gdd`). Dates are `YYYY-MM-DD`.
Seasons: chill runs Nov 1 to Oct 31 (label `2025-26`), GDD runs Jan 1 to Dec 31 (label `2026`).
`issue_date` is the last full day of readings; the forecast covers the 7 days after it.

## Run it

```
pip install -r requirements.txt
cd forecast
python daily_forecast.py train      # once, saves models/daily_forecast.joblib
export CIMIS_APP_KEY=...            # optional: fresh CIMIS readings at start-up and every 6 hours
uvicorn api:app --port 8000
```

Without `CIMIS_APP_KEY` the API serves the forecast from the last day in the hourly CSV.

## Endpoints

| Method and path | Use it for |
| --- | --- |
| `GET /api/health` | Data freshness: issue date, where the data came from, last refresh error |
| `GET /api/stations` | Station list for the picker and map markers |
| `GET /api/stations/{station}/summary?measure=` | The headline tiles: so far, next 7 days, projected, vs past seasons |
| `GET /api/stations/{station}/seasons?measure=` | Running-total chart: this season (observed then forecast) against past seasons |
| `GET /api/forecast?station=` | Daily 7-day forecast rows (all stations if `station` is left out) |
| `GET /api/map?measure=&value=` | Contour map grid between stations; `value` = `next7`, `season_to_date` or `projected` |
| `GET /api/point?lat=&lon=&measure=` | The same numbers for any orchard location, kriged from the five stations |
| `POST /api/refresh` | Pull from CIMIS now and re-forecast (needs `CIMIS_APP_KEY` on the server) |

Errors: unknown station → 404, bad `measure` or `value` → 422, refresh without a key → 400,
refresh that fails at CIMIS → 502 (the API keeps serving the last good forecast).

## Example responses

Lists below are cut to their first items.

### GET /api/health
```json
{
  "status": "ok",
  "issue_date": "2026-10-22",
  "source": "archive",
  "refreshed_at": "2026-10-24T16:44:27+00:00",
  "live_updates": false,
  "model_trained_through": "2026-10-22",
  "last_error": null
}
```

### GET /api/stations
```json
[
  {
    "station": 5,
    "name": "Shafter",
    "latitude": 35.53256,
    "longitude": -119.28179,
    "elevation_ft": 360.0
  },
  {
    "station": 6,
    "name": "Davis",
    "latitude": 38.53569,
    "longitude": -121.77636,
    "elevation_ft": 60.0
  }
]
```

### GET /api/stations/6/summary?measure=gdd

`pct_vs_past` compares `season_to_date` with the average of past seasons on the same day of the season.
`normal_next7` is what the next 7 days usually bring. `days_missing` counts days with too few readings.
```json
{
  "station": 6,
  "measure": "gdd",
  "units": "degree-days (F)",
  "issue_date": "2026-10-22",
  "season": "2026",
  "season_start": "2026-01-01",
  "season_to_date": 4595.13,
  "days_missing": 1,
  "next7": 66.43,
  "normal_next7": 73.09,
  "projected": 4661.56,
  "projected_through": "2026-10-29",
  "past_seasons_same_date": [
    {
      "season": "2025",
      "total": 4186.8
    },
    {
      "season": "2024",
      "total": 4449.87
    },
    {
      "season": "2023",
      "total": 3795.39
    },
    {
      "season": "2022",
      "total": 4389.3
    }
  ],
  "past_avg_same_date": 4205.34,
  "pct_vs_past": 9.3
}
```

### GET /api/stations/6/seasons?measure=gdd

`day` counts days since the season started, so seasons line up on one x axis. In the current
season, points after `issue_date` have `kind: "forecast"`.
```json
{
  "station": 6,
  "measure": "gdd",
  "units": "degree-days (F)",
  "issue_date": "2026-10-22",
  "seasons": [
    {
      "season": "2026",
      "current": true,
      "points": [
        {
          "day": 0,
          "date": "2026-01-01",
          "total": 2.07,
          "kind": "observed"
        },
        {
          "day": 301,
          "date": "2026-10-29",
          "total": 4661.56,
          "kind": "forecast"
        }
      ]
    },
    {
      "season": "2025",
      "current": false,
      "points": [
        {
          "day": 0,
          "date": "2025-01-01",
          "total": 0.0,
          "kind": "observed"
        },
        {
          "day": 364,
          "date": "2025-12-31",
          "total": 4551.48,
          "kind": "observed"
        }
      ]
    }
  ]
}
```

### GET /api/forecast?station=6
```json
[
  {
    "station": 6,
    "issue_date": "2026-10-22",
    "target_date": "2026-10-23",
    "horizon": 1,
    "chill_hours": 0.0,
    "chill_portions": 0.04,
    "gdd": 8.56,
    "chill_hours_season_to_date": 918.0,
    "chill_portions_season_to_date": 67.22,
    "gdd_season_to_date": 4603.69
  }
]
```

### GET /api/map?measure=gdd&value=next7

1,358 points about 5 km apart, within 35 km of the line through the stations. `nearest_km` can
fade out points far from any station.
```json
{
  "measure": "gdd",
  "value": "next7",
  "units": "degree-days (F)",
  "issue_date": "2026-10-22",
  "stations": [
    {
      "station": 5,
      "value": 78.87
    },
    {
      "station": 6,
      "value": 66.43
    }
  ],
  "points": [
    {
      "lat": 35.233,
      "lon": -119.376,
      "value": 78.72,
      "nearest_km": 34.4
    },
    {
      "lat": 35.233,
      "lon": -119.326,
      "value": 78.76,
      "nearest_km": 33.6
    }
  ]
}
```

### GET /api/point?lat=37.8&lon=-121.1&measure=gdd

`rough_estimate` is true when the nearest station is more than 35 km away. `weights` shows how much
each station contributes.
```json
{
  "lat": 37.8,
  "lon": -121.1,
  "measure": "gdd",
  "units": "degree-days (F)",
  "issue_date": "2026-10-22",
  "nearest_station": 70,
  "nearest_km": 11.5,
  "rough_estimate": false,
  "weights": {
    "5": -0.008,
    "6": 0.01,
    "39": 0.034,
    "70": 0.66,
    "71": 0.305
  },
  "season_to_date": 4601.29,
  "next7": 71.47,
  "normal_next7": 69.25,
  "projected": 4672.76,
  "past_avg_same_date": 4181.32,
  "daily": [
    {
      "date": "2026-10-23",
      "gdd": 11.43
    },
    {
      "date": "2026-10-24",
      "gdd": 11.55
    }
  ]
}
```
