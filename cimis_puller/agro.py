"""Chill and growing-degree-day calculations (UC Davis FNRIC conventions).

All functions take temperatures in degrees Fahrenheit. References:
  https://fruitsandnuts.ucdavis.edu/about-chilling-hours-units-and-portions
  https://fruitsandnuts.ucdavis.edu/weather-models

Models:
  chill hours     1 per hour with 32F <= T <= 45F
  Utah units      Richardson et al. 1974 weights, negative above 60F
  chill portions  Dynamic model (Fishman/Erez), same parameters as R chillR
  GDD             simple average method: max(0, (tmax + tmin) / 2 - base)
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def f_to_c(t):
    return (t - 32.0) * 5.0 / 9.0


def c_to_f(t):
    return t * 9.0 / 5.0 + 32.0


def chill_hours(temps_f: pd.Series) -> pd.Series:
    """1.0 for each hour in [32, 45] F, 0.0 otherwise, NaN where temp is missing."""
    out = ((temps_f >= 32) & (temps_f <= 45)).astype(float)
    return out.where(temps_f.notna())


def utah_chill_units(temps_f: pd.Series) -> pd.Series:
    """Per-hour Utah chill units (Richardson 1974), NaN where temp is missing."""
    t = temps_f
    conds = [t <= 34, t <= 45, t <= 55, t <= 60, t <= 65, t <= 70, t > 70]
    vals = [0.0, 0.5, 1.0, 0.5, 0.0, -0.5, -1.0]
    return pd.Series(np.select(conds, vals, default=np.nan), index=t.index).where(t.notna())


# Dynamic model parameters (Fishman et al. 1987; as used in chillR::Dynamic_Model).
_E0, _E1 = 4153.5, 12888.8
_A0, _A1 = 139500.0, 2.567e18
_SLP, _TETMLT = 1.6, 277.0


def dynamic_chill_portions(temps_f: pd.Series, reset: pd.Series | None = None) -> pd.Series:
    """Chill portions earned each hour under the Dynamic model.

    temps_f must be one station's hourly series in time order. The model is
    stateful: an intermediate product builds up and is converted to a
    permanent portion once it passes 1. `reset` (bool, same index) zeroes that
    state, e.g. at the start of each chill season. A missing hour leaves the
    state unchanged and earns nothing.
    """
    temps_k = f_to_c(temps_f.to_numpy(dtype=float)) + 273.0
    resets = reset.to_numpy(dtype=bool) if reset is not None else np.zeros(len(temps_k), bool)
    out = np.full(len(temps_k), np.nan)
    aa, ee = _A0 / _A1, _E1 - _E0
    inter = 0.0      # intermediate product E at the end of the previous hour
    xi_prev = 0.0
    for i, tk in enumerate(temps_k):
        if resets[i]:
            inter, xi_prev = 0.0, 0.0
        if math.isnan(tk):
            continue
        sr = math.exp(_SLP * _TETMLT * (tk - _TETMLT) / tk)
        xi = sr / (1.0 + sr)
        xs = aa * math.exp(ee / tk)
        ak1 = _A1 * math.exp(-_E1 / tk)
        start = inter if inter < 1 else inter - inter * xi_prev
        inter = xs - (xs - start) * math.exp(-ak1)
        out[i] = inter * xi if inter >= 1 else 0.0
        xi_prev = xi
    return pd.Series(out, index=temps_f.index)


def gdd(tmax_f: pd.Series, tmin_f: pd.Series, base_f: float = 50.0) -> pd.Series:
    """Daily growing degree days, simple average method, NaN if either temp is missing."""
    return ((tmax_f + tmin_f) / 2 - base_f).clip(lower=0)


def season_id(ts: pd.Series, start_mmdd: str) -> pd.Series:
    """Label each timestamp with the year its season started.

    With start_mmdd="11-01", 2022-01-15 belongs to season 2021.
    """
    m, d = (int(x) for x in start_mmdd.split("-"))
    ts = pd.to_datetime(ts)
    before = (ts.dt.month < m) | ((ts.dt.month == m) & (ts.dt.day < d))
    return ts.dt.year - before.astype(int)
