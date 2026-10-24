"""Daily chill and GDD forecast for the next 7 days at each CIMIS station.

For an issue date t (after day t's readings are in), predicts for each day t+1..t+7:
chill hours (32-45F), chill portions (Dynamic model) and GDD (base 50F).

Method: for each quantity and each lead day, one gradient-boosting model shared by all
stations predicts the departure from that station's normal for the target day (daily
climatology), using the last week of readings, recent temperature trend, what the other
stations saw, season timing, location and station id. Each lead day's forecast is then a
weighted blend of that model, persistence (today's value) and climatology, with weights
chosen on held-out seasons: near-term days lean on recent readings, later days on normals.

Data source: any hourly CIMIS table with station, timestamp_pst, hly-air-tmp, hly-air-tmp_qc,
like the uploaded CSV. `live` fetches the latest weeks from the CIMIS API with
cimis_puller/cimis_pull.py into that same format and forecasts from them, so the model
trained on the file keeps producing current forecasts. Only the last 7 days are needed.

Usage:
    python daily_forecast.py train      # fit on training years, score the test year, refit on all data, save
    python daily_forecast.py predict [--hourly FILE] [--issue-date YYYY-MM-DD] [--out FILE]
    python daily_forecast.py live       # pull the last 3 weeks from the CIMIS API (CIMIS_APP_KEY), then predict
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from baselines import HERE, TARGETS, TEST_START, daily_from_hourly, load_hourly
import agro  # noqa: E402,I001  (importing baselines puts cimis_puller on sys.path)

HORIZONS = range(1, 8)
DEFAULT_HOURLY = HERE / "data/cimis_hourly_2021-10-23_2026-10-22.csv"
DEFAULT_STATIONS = HERE / "data/cimis_stations_selected.csv"
MODEL_PATH = HERE / "models/daily_forecast.joblib"
MAX_DAILY = {"chill_hours": 24.0, "chill_portions": np.inf, "gdd": np.inf}
SEASONS = {"chill_hours": [11, 12, 1, 2], "chill_portions": [11, 12, 1, 2], "gdd": list(range(3, 11))}


def daily_climatology(daily: pd.DataFrame, before: pd.Timestamp | None = None) -> pd.DataFrame:
    """Mean of each quantity by station and day of year (+-7 days, circular)."""
    d = daily if before is None else daily[daily["date"] < before]
    d = d.assign(doy=d["date"].dt.dayofyear.clip(upper=365))
    out = []
    for c in TARGETS:
        by = d.groupby(["station", "doy"])[c].mean().unstack("doy").reindex(columns=range(1, 366))
        wrapped = pd.concat([by.iloc[:, -7:], by, by.iloc[:, :7]], axis=1)
        smooth = wrapped.T.rolling(15, center=True, min_periods=1).mean().T.iloc[:, 7:-7]
        smooth.columns = pd.Index(range(1, 366), name="doy")
        out.append(smooth.stack().rename(f"clim_{c}"))
    return pd.concat(out, axis=1).reset_index()


def issue_features(daily: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """One row per station and issue date with everything known at the end of that day."""
    parts = []
    for _, g in daily.groupby("station"):
        g = g.set_index("date").asfreq("D")
        g["station"] = g["station"].ffill().bfill()
        g["tmean"] = (g["tmax"] + g["tmin"]) / 2
        f = pd.DataFrame(index=g.index)
        for c in TARGETS + ["tmax", "tmin", "tmean"]:
            for lag in range(7):
                f[f"{c}_lag{lag}"] = g[c].shift(lag)
            f[f"{c}_7d"] = g[c].rolling(7, min_periods=5).mean()
        f["tmean_trend"] = g["tmean"].rolling(3, min_periods=2).mean() - g["tmean"].shift(3).rolling(4, min_periods=3).mean()
        f["station"] = g["station"].astype(int)
        parts.append(f.reset_index())
    f = pd.concat(parts, ignore_index=True)
    # what the other stations saw yesterday-to-today (all five report hourly)
    wide = f.pivot(index="date", columns="station", values="tmean_lag0")
    others = wide.apply(lambda col: wide.drop(columns=col.name).mean(axis=1))
    f = f.merge(others.stack().rename("others_tmean").reset_index(), on=["date", "station"], how="left")
    f["tmean_vs_others"] = f["tmean_lag0"] - f["others_tmean"]
    return f.merge(stations[["station", "latitude", "longitude", "elevation_ft"]], on="station", how="left")


def expand_horizons(feats: pd.DataFrame, clim: pd.DataFrame, daily: pd.DataFrame | None) -> pd.DataFrame:
    """Repeat each issue row for lead days 1..7, attaching the target day's climatology (and truth if known)."""
    rows = []
    for h in HORIZONS:
        x = feats.copy()
        x["horizon"] = h
        x["target_date"] = x["date"] + pd.Timedelta(days=h)
        rows.append(x)
    x = pd.concat(rows, ignore_index=True)
    x["doy"] = x["target_date"].dt.dayofyear.clip(upper=365)
    ang = 2 * np.pi * x["doy"] / 365
    x["doy_sin"], x["doy_cos"] = np.sin(ang), np.cos(ang)
    x = x.merge(clim, on=["station", "doy"], how="left")
    for c in TARGETS:
        # how far recent days ran from the target day's normal (trees can't subtract two features)
        x[f"{c}_lag0_anom"] = x[f"{c}_lag0"] - x[f"clim_{c}"]
        x[f"{c}_7d_anom"] = x[f"{c}_7d"] - x[f"clim_{c}"]
    if daily is not None:
        truth = daily[["station", "date"] + TARGETS].rename(columns={"date": "target_date", **{c: f"y_{c}" for c in TARGETS}})
        x = x.merge(truth, on=["station", "target_date"], how="left")
    return x


def feature_cols(c: str, frame: pd.DataFrame) -> list[str]:
    lagged = [col for col in frame.columns if any(col.startswith(p) for p in (c, "tmax", "tmin", "tmean")) and
              (col.endswith("_7d") or "_lag" in col) and not col.endswith("_anom")]
    return lagged + [f"{c}_lag0_anom", f"{c}_7d_anom", "tmean_trend", "others_tmean", "tmean_vs_others", f"clim_{c}", "horizon",
                     "doy_sin", "doy_cos", "latitude", "longitude", "elevation_ft", "station"]


def _hgb() -> HistGradientBoostingRegressor:
    # absolute-error loss predicts the median: many days have exactly 0 chill hours or
    # 0 GDD, and a squared-error model smears small positive values over those runs
    return HistGradientBoostingRegressor(loss="absolute_error", max_iter=200, learning_rate=0.07,
                                         max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.0,
                                         categorical_features=["station"], random_state=0)


def _fit_models(x: pd.DataFrame, c: str) -> dict:
    """One model per lead day (direct strategy), each predicting the departure from normal."""
    out = {}
    for h in HORIZONS:
        tr = x[x["horizon"] == h].dropna(subset=[f"y_{c}", f"clim_{c}"])
        cols = feature_cols(c, tr)
        out[h] = (_hgb().fit(tr[cols], tr[f"y_{c}"] - tr[f"clim_{c}"]), cols)
    return out


def _candidates(models: dict, x: pd.DataFrame, c: str) -> np.ndarray:
    """Columns: model, persistence (today's value), climatology."""
    model = np.full(len(x), np.nan)
    for h, (m, cols) in models.items():
        rows = (x["horizon"] == h).to_numpy()
        if rows.any():
            model[rows] = x.loc[rows, f"clim_{c}"].to_numpy() + m.predict(x.loc[rows, cols])
    return np.column_stack([model, x[f"{c}_lag0"].to_numpy(), x[f"clim_{c}"].to_numpy()])


SIMPLEX = np.array([(i / 10, j / 10, (10 - i - j) / 10) for i in range(11) for j in range(11 - i)])


def fit(x: pd.DataFrame) -> dict:
    """Per-lead-day models plus, per lead day, a blend of model / persistence / climatology.

    Without weather-forecast inputs the model's edge fades after a few days, and which of
    the three is best changes from year to year. So the blend weights are chosen
    out of sample: each training season in turn is held out, models are fit on the other
    seasons, and the weights (on a 0.1 grid, summing to 1) minimise mean absolute error
    over all held-out seasons together. The models are then refit on all of x.
    """
    x = x.assign(season=x["target_date"].dt.year - (x["target_date"].dt.month < 11))
    bundle = {}
    for c in TARGETS:
        cands, truths, hs = [], [], []
        for s in sorted(x["season"].unique()):
            held = x[(x["season"] == s) & x["target_date"].dt.month.isin(SEASONS[c])]
            if held[f"y_{c}"].notna().sum() < 100:
                continue
            # leave a week's gap so no training target overlaps the held-out season's inputs
            rest = x[(x["season"] != s) & ((x["target_date"] < held["date"].min() - pd.Timedelta(days=7)) |
                                          (x["date"] > held["target_date"].max() + pd.Timedelta(days=7)))]
            cands.append(_candidates(_fit_models(rest, c), held, c))
            truths.append(held[f"y_{c}"].to_numpy())
            hs.append(held["horizon"].to_numpy())
        cand, y, hz = np.vstack(cands), np.concatenate(truths), np.concatenate(hs)
        weights = {}
        for h in HORIZONS:
            ok = (hz == h) & ~np.isnan(cand).any(axis=1) & ~np.isnan(y)
            err = np.abs(np.clip(cand[ok] @ SIMPLEX.T, 0, MAX_DAILY[c]) - y[ok, None]).mean(axis=0)
            weights[h] = SIMPLEX[err.argmin()]
        bundle[c] = {"models": _fit_models(x, c), "weights": weights}
    return bundle


def predict_frame(bundle: dict, x: pd.DataFrame) -> pd.DataFrame:
    out = x[["station", "date", "target_date", "horizon"]].rename(columns={"date": "issue_date"}).copy()
    for c, b in bundle.items():
        cand = _candidates(b["models"], x, c)
        # a missing reading today drops persistence; fall back to model + climatology
        cand[:, 1] = np.where(np.isnan(cand[:, 1]), cand[:, 0], cand[:, 1])
        w = np.vstack([b["weights"][h] for h in x["horizon"]])
        out[c] = np.clip((cand * w).sum(axis=1), 0, MAX_DAILY[c])
    return out


def mae(a, b) -> float:
    m = pd.concat([pd.Series(a), pd.Series(b)], axis=1).dropna()
    return float((m.iloc[:, 0] - m.iloc[:, 1]).abs().mean())


def train(args) -> None:
    stations = pd.read_csv(args.stations)
    daily = daily_from_hourly(load_hourly(args.hourly))
    feats = issue_features(daily, stations)

    # 1. honest score: train before the test year, test on it
    x = expand_horizons(feats, daily_climatology(daily, before=TEST_START), daily)
    train_x = x[x["target_date"] < TEST_START]
    test_x = x[x["date"] >= TEST_START]
    eval_bundle = fit(train_x)
    pred = predict_frame(eval_bundle, test_x)
    rows = []
    for c in TARGETS:
        t = test_x.assign(pred=pred[c].to_numpy())
        t = t[t["target_date"].dt.month.isin(SEASONS[c])]
        for h, g in t.groupby("horizon"):
            rows.append({"target": c, "horizon_days": h, "n": int(g[f"y_{c}"].notna().sum()),
                         "mean_daily": g[f"y_{c}"].mean(),
                         "persistence": mae(g[f"y_{c}"], g[f"{c}_lag0"]),
                         "climatology": mae(g[f"y_{c}"], g[f"clim_{c}"]),
                         "model": mae(g[f"y_{c}"], g["pred"]),
                         "blend_weights_model_persist_clim": " / ".join(f"{v:.2f}" for v in eval_bundle[c]["weights"][h])})
    scores = pd.DataFrame(rows)
    scores.to_csv(HERE / "daily_forecast_scores.csv", index=False)
    pred.merge(test_x[["station", "target_date", "horizon"] + [f"y_{c}" for c in TARGETS]],
               on=["station", "target_date", "horizon"]).to_csv(HERE / "daily_forecast_test_predictions.csv", index=False)
    pd.set_option("display.width", 200)
    print(scores.round(2).to_string(index=False))

    # 2. production model: refit on every year, climatology from every year
    clim_all = daily_climatology(daily)
    x_all = expand_horizons(feats, clim_all, daily)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"models": fit(x_all), "climatology": clim_all, "trained_through": str(daily["date"].max().date())},
                MODEL_PATH)
    print(f"saved {MODEL_PATH}", file=sys.stderr)


def predict(args) -> None:
    bundle = joblib.load(MODEL_PATH)
    stations = pd.read_csv(args.stations)
    daily = daily_from_hourly(load_hourly(args.hourly))
    issue = pd.Timestamp(args.issue_date) if args.issue_date else daily.dropna(subset=["gdd"])["date"].max()
    feats = issue_features(daily[daily["date"] <= issue], stations)
    x = expand_horizons(feats[feats["date"] == issue], bundle["climatology"], None)
    out = predict_frame(bundle["models"], x)

    # season-to-date totals so the output answers "so far" and "projected" together
    # (a forecast day past Nov 1 / Jan 1 starts the new season's count from zero)
    hist = daily[daily["date"] <= issue].copy()
    out = out.sort_values(["station", "target_date"])
    for c, start in [("chill_hours", "11-01"), ("chill_portions", "11-01"), ("gdd", "01-01")]:
        season = agro.season_id(out["target_date"], start)
        so_far = hist[agro.season_id(hist["date"], start) == agro.season_id(pd.Series([issue]), start).iloc[0]]
        so_far = so_far.groupby("station")[c].sum()
        same = season == agro.season_id(pd.Series([issue]), start).iloc[0]
        out[f"{c}_season_to_date"] = (out["station"].map(so_far).where(same, 0)
                                      + out.groupby(["station", season])[c].cumsum())
    out.to_csv(args.out, index=False, float_format="%.2f")
    print(out.round(1).to_string(index=False))
    print(f"wrote {args.out} (issue date {issue.date()}, model trained through {bundle['trained_through']})",
          file=sys.stderr)


def fetch_live(stations: pd.DataFrame, days: int, app_key: str) -> pd.DataFrame:
    """Last `days` days of hourly air temperature from the CIMIS API, in the uploaded file's format."""
    sys.path.insert(0, str(HERE.parent / "cimis_puller"))
    import cimis_pull as cp

    client = cp.CimisClient(app_key)
    end = pd.Timestamp.now(tz="Etc/GMT+8").date()
    start = end - pd.Timedelta(days=days)
    rows = []
    for st in stations["station"]:
        for rec in client.data(int(st), start, end, items=["hly-air-tmp"], unit="M"):
            rows.append({"station": int(st), "date": rec.get("date"), "hour": rec.get("hour"),
                         "hly-air-tmp": rec.get("hly_air_tmp"), "hly-air-tmp_qc": rec.get("hly_air_tmp_qc") or None})
    live = pd.DataFrame(rows)
    hrs = pd.to_numeric(live["hour"], errors="coerce") // 100  # CIMIS hour 2400 = next day's 00:00
    live["timestamp_pst"] = pd.to_datetime(live["date"]) + pd.to_timedelta(hrs, unit="h")
    return live[["station", "timestamp_pst", "hly-air-tmp", "hly-air-tmp_qc"]]


def live(args) -> None:
    """Pull the latest weeks from the CIMIS API and forecast from them with the saved model."""
    key = args.app_key or os.environ.get("CIMIS_APP_KEY")
    if not key:
        sys.exit("set CIMIS_APP_KEY (or pass --app-key) to pull live readings")
    path = HERE / "data/live_hourly.csv"
    fresh = fetch_live(pd.read_csv(args.stations), args.days, key)
    # keep the archive underneath so season-to-date totals still start at the season start
    archive = pd.read_csv(args.hourly, usecols=fresh.columns.tolist(), parse_dates=["timestamp_pst"])
    combined = pd.concat([archive, fresh]).drop_duplicates(["station", "timestamp_pst"], keep="last")
    combined.sort_values(["station", "timestamp_pst"]).to_csv(path, index=False)
    print(f"pulled {len(fresh):,} live readings; archive + live saved to {path}", file=sys.stderr)
    args.hourly = path
    predict(args)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["train", "predict", "live"])
    ap.add_argument("--hourly", type=Path, default=DEFAULT_HOURLY)
    ap.add_argument("--stations", type=Path, default=DEFAULT_STATIONS)
    ap.add_argument("--issue-date", help="forecast as of the end of this day (default: last full day in the data)")
    ap.add_argument("--out", type=Path, default=HERE / "forecast_output.csv")
    ap.add_argument("--days", type=int, default=21, help="live: days of recent readings to pull")
    ap.add_argument("--app-key", help="live: CIMIS app key (default: CIMIS_APP_KEY env var)")
    args = ap.parse_args(argv)
    {"train": train, "predict": predict, "live": live}[args.command](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
