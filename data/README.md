# CIMIS hourly station data, 5 years

Hourly weather data for 5 CIMIS stations, **2021-10-23 through 2026-10-22**, pulled from the
CIMIS Web API on 2026-10-23. Values are unmodified from the API; the only transformation is
JSON → CSV.

| Station | Name | County | Lat | Lon | Elev (ft) |
|---|---|---|---|---|---|
| 5 | Shafter | Kern | 35.532556 | −119.28179 | 360 |
| 6 | Davis | Yolo | 38.535694 | −121.77636 | 60 |
| 39 | Parlier | Fresno | 36.597444 | −119.50404 | 337 |
| 70 | Manteca | San Joaquin | 37.834822 | −121.22319 | 33 |
| 71 | Modesto | Stanislaus | 37.645222 | −121.18776 | 35 |

## Files

| File | Rows | Size | SHA-256 |
|---|---|---|---|
| `cimis_hourly_2021-10-23_2026-10-22.csv` | 219,120 + header | 25.2 MB | `3d4de18b557e49c8cbe4e3c895ff03234452d13e4926c7892cec3a2345fb66f4` |
| `cimis_stations_selected.csv` | 5 + header | 4.6 KB | `75d9d4e4cb05caf7247ce0156077328b7e4b3edd91df01a7e8917f8792e37fc6` |

Files are UTF-8 with `\n` line endings. `data/.gitattributes` stops Git from converting them
on checkout, so the checksums match on Windows and Mac.

### `cimis_hourly_…csv` columns (wide: one row per station-hour)

| Column | Meaning |
|---|---|
| `station` | CIMIS station number |
| `date` | CIMIS date, `YYYY-MM-DD` |
| `hour` | CIMIS hour label `0100`…`2400`, kept as text |
| `julian` | Day of year |
| `timestamp_pst` | End of the hour, Pacific **Standard** Time year-round (CIMIS doesn't use daylight saving). `date` + `hour`, so hour `2400` becomes the next day's `00:00`. |
| `hly-<item>` | Value, metric units (below). Empty = no value. |
| `hly-<item>_qc` | CIMIS QC flag for that value. Empty = no flag. |

Items and units: `air-tmp` °C, `dew-pnt` °C, `net-rad` W/m², `asce-eto` mm, `asce-etr` mm,
`precip` mm, `rel-hum` %, `res-wind` m/s, `soil-tmp` °C, `sol-rad` W/m², `vap-pres` kPa,
`wind-dir` degrees, `wind-spd` m/s.

### `cimis_stations_selected.csv`

Station metadata from `/StationWeb/GetAllStations`. Latitude and longitude are decimal degrees,
elevation is in feet. `siting_desc` is CIMIS's site notes, flattened from HTML into one
` | `-separated line.

## How it was downloaded

- **API:** `GET https://et.water.ca.gov/StationWeb/GetDataByStationNumber` with
  `stationNbrs, startDate, endDate, isHourly=true, unitOfMeasure=M, dataItems=<13 items>`.
- **Auth:** the CIMIS "Web API App Key" goes in the `Ocp-Apim-Subscription-Key` header.
  The old form (`https://et.water.ca.gov/api/data?appKey=…`) is blocked by CIMIS's firewall
  for current keys. The key isn't stored anywhere in this repo.
- **Request size:** found by probing. An hourly request may hold at most **5,020 records**,
  where a record is one station-hour; the number of data items doesn't count. Above that, the
  API returns `ERR2112-DATA VOLUME VIOLATION`.
  - Each request was 1 station × 208 days = 4,992 records.
  - That makes 9 chunks per station, 45 requests in total. The minimum possible is 44 (219,120 / 5,020).
  - 4 requests ran in parallel. The run took 56 s, with no retries or errors.
- **Item list:** `hly-eto` appears in CIMIS's docs, but the API rejects it (`ERR1035`), so it
  was left out. The other 13 hourly items were requested.
- **Scripts:** these are in the parent hackathon folder, outside this repo: `cimis_fetch.py`
  (request and parsing), `cimis_bulk.py` (chunking, parallel download, cache) and
  `cimis_stations.py` (station list). To reproduce:

```bash
export CIMIS_APP_KEY=<key>      # PowerShell: $env:CIMIS_APP_KEY="<key>"
python cimis_bulk.py --stations 6,70,71,39,5 --start 2021-10-23 --end 2026-10-22 \
    --out git_repo/data/cimis_hourly_2021-10-23_2026-10-22.csv --workers 4
python cimis_stations.py --out data/cimis_stations.csv   # then filter to the 5 stations
```

A re-download should give the same rows. The checksum may still change if CIMIS later revises
QC flags or backfills values; that's expected for recent months.

## Verification done (expected results)

1. **Completeness:** each station has exactly 43,824 rows (1,826 days × 24), from
   `2021-10-23 01:00` to `2026-10-23 00:00`. There are 0 duplicate timestamps and 0 gaps in
   the hourly grid.
2. **Hour labels:** exactly 24 distinct values, `0100`…`2400`.
3. **Spot check against a fresh API call (cache bypassed):** all values and flags matched for
   these station-days:
   - st5 2025-10-19
   - st39 2026-04-28
   - st71 2025-01-12
4. **Ranges:** all values are physically plausible except the known sensor failures listed
   below. Air temp is −4.5 to 45.5 °C, solar radiation 0 to 1,141 W/m², precipitation 0 to
   16.8 mm per hour.

Snippet to re-check items 1–2:

```python
import pandas as pd
df = pd.read_csv("cimis_hourly_2021-10-23_2026-10-22.csv", parse_dates=["timestamp_pst"],
                 keep_default_na=False, na_values=[""], dtype={"hour": str})
assert len(df) == 219_120 and df.hour.nunique() == 24
for st, g in df.groupby("station"):
    t = g.timestamp_pst.sort_values()
    assert len(g) == 43_824 and t.is_unique and (t.diff().dropna() == pd.Timedelta("1h")).all(), st
```

## Things to know before using it

- **ETr (`hly-asce-etr`) is always empty and flagged `N` at every station.** CIMIS doesn't
  publish it for these stations.
- **Shafter (5) stopped being an ETo station.** From `2024-06-14 11:00` onward, net radiation
  and ETo are empty and flagged `N` ("not collected"), so 47% of the 5 years are missing for
  those two items. The station list shows `is_eto_station=False`. All other Shafter sensors
  keep reporting.
- **Missing hours:** under 0.5% for every item except soil temperature and the cases above.
  Soil temperature is missing 9.2% at Shafter, 6.5% at Manteca and 2.2% at Parlier.
- **Real sensor failures that CIMIS did NOT flag.** In both cases humidity reads 0%, dew point
  reads about −45 to −64 °C and vapor pressure reads about 0.01 kPa, while air temperature
  looks normal. CIMIS flagged roughly half of these hours `Q`/`S` and left the rest blank, so
  the QC flags alone miss them.
  - Parlier (39), 2022-01-28 11:00 to 2022-02-03 09:00: 101 unflagged hours.
  - Manteca (70), 2021-12-07 12:00 to 2021-12-21 12:00: 72 unflagged hours.
- **A flag doesn't always mean the value is wrong.** `R`/`Y` mean "outside historical range"
  and can be real extreme weather. Wind `I` is set whenever wind ≤ 0.447 m/s (1 mph, the
  sensor's floor). That's why wind speed never goes below 0.45.

### QC flags seen in this data

From the official legend ([CurrentFlags2.pdf](https://cimis-legacy.water.ca.gov/Content/PDF/CurrentFlags2.pdf)).
CIMIS notes that the same flag can mean different things for different items.

| Flag | Type | Meaning |
|---|---|---|
| `M` | severe | Missing |
| `S` | severe | Sensor not in service or out of sensor threshold. For air temp, also "constant 4 hours in a row". |
| `I` | severe | No meaning / ignore. For wind, ≤ 0.447 m/s or constant 4 hours. |
| `Q` | informative | Full QC not possible because a comparison sensor is severe |
| `R` | informative | Far out of historical limits (outside the 99.8% interval), or an item-specific check failed. For example, an air temp jump of more than 10 °C in an hour. |
| `Y` | informative | Moderately out of historical limits (outside the 96% interval) |
| `N` | informative | Not collected by this station |
| `A` | informative | Historical average substituted |
| `E`, `T` | informative | Historical average used for one of the input sensors |

Counts of each flag per item:

| Item | A | E | I | M | N | Q | R | S | T | Y |
|---|---|---|---|---|---|---|---|---|---|---|
| air-tmp | | | | 393 | | | 433 | 110 | | 7,848 |
| asce-eto | 396 | 2 | | 186 | 20,654 | | 4,873 | | | 6,979 |
| asce-etr | | | | 1 | 219,119 | | | | | |
| dew-pnt | | | | 393 | | 304 | 435 | | | 7,854 |
| net-rad | | 191 | | 283 | 20,654 | 1 | 407 | | 107 | |
| precip | | | | 390 | | | 55 | | | 126 |
| rel-hum | | | | 393 | | 304 | 435 | | | 7,854 |
| res-wind | | | 4,595 | 426 | | 2 | 3,185 | | | |
| soil-tmp | | | | 1,972 | | | 3,453 | 6,066 | | 11,413 |
| sol-rad | | | | 391 | | | 3 | | | 94 |
| vap-pres | | | | 393 | | 109 | 2 | 195 | | 10 |
| wind-dir | | | | 390 | | | 36 | | | |
| wind-spd | | | 4,595 | 390 | | | | 2 | | |
