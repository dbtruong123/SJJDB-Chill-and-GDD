"""Rolling-origin backtest: refit the daily forecaster for each test year using only earlier data.

    python validation/backtest.py            # writes validation/backtest_scores.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import daily_forecast as d  # noqa: E402
from baselines import daily_from_hourly, load_hourly  # noqa: E402

FOLDS = ["2023-10-23", "2024-10-23", "2025-10-23"]


def main() -> None:
    stations = pd.read_csv(d.DEFAULT_STATIONS)
    daily = daily_from_hourly(load_hourly(d.DEFAULT_HOURLY))
    feats = d.issue_features(daily, stations)
    rows = []
    for start in map(pd.Timestamp, FOLDS):
        end = start + pd.DateOffset(years=1)
        x = d.expand_horizons(feats, d.daily_climatology(daily, before=start), daily)
        train_x = x[x["target_date"] < start]
        test_x = x[(x["date"] >= start) & (x["date"] < end)]
        pred = d.predict_frame(d.fit(train_x), test_x)
        for c in d.TARGETS:
            t = test_x.assign(pred=pred[c].to_numpy())
            t = t[t["target_date"].dt.month.isin(d.SEASONS[c])]
            for h, g in t.groupby("horizon"):
                rows.append({"test_year": f"{start.year}-{start.year + 1}", "train_years": start.year - 2021,
                             "target": c, "horizon_days": h, "n": int(g[f"y_{c}"].notna().sum()),
                             "persistence": d.mae(g[f"y_{c}"], g[f"{c}_lag0"]),
                             "climatology": d.mae(g[f"y_{c}"], g[f"clim_{c}"]),
                             "model": d.mae(g[f"y_{c}"], g["pred"])})
        print(f"fold {start.date()} done", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(Path(__file__).with_name("backtest_scores.csv"), index=False, float_format="%.3f")
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
