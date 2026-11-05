# Author: Pradeep Sahoo — Retail Nexus AI
"""Baseline + ensemble forecasting for product-store demand.

Baselines: seasonal naive (lag-7), exponential moving average.
Upgrade: a lightweight GradientBoostingRegressor on calendar + lag features.

All models are stateless over the input series; features are built per-series so
we can serve a forecast without a trained global model. The GBM is trained once per
call using the past window — cheap on these series lengths and avoids drift.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd


def _series(hist: pd.DataFrame) -> pd.Series:
    s = hist["units_sold"].astype(float).copy()
    s.index = pd.to_datetime(s.index)
    return s


def seasonal_naive(hist: pd.DataFrame, horizon_days: int) -> list[tuple[date, float]]:
    s = _series(hist)
    if len(s) < 7:
        last = float(s.iloc[-1]) if len(s) else 0.0
        return [(pd.Timestamp(s.index[-1] if len(s) else pd.Timestamp.today()).date() + timedelta(days=i+1), last) for i in range(horizon_days)]
    out = []
    for i in range(horizon_days):
        d = s.index[-1] + pd.Timedelta(days=i + 1)
        val = float(s.iloc[-7 + (i % 7)])
        out.append((d.date(), val))
    return out


def ema(hist: pd.DataFrame, horizon_days: int, alpha: float = 0.3) -> list[tuple[date, float]]:
    s = _series(hist)
    if len(s) == 0:
        return []
    level = s.iloc[-1]
    for v in s.iloc[:-1][::-1]:
        level = alpha * v + (1 - alpha) * level
    out = []
    for i in range(horizon_days):
        d = s.index[-1] + pd.Timedelta(days=i + 1)
        out.append((d.date(), float(max(0.0, level))))
    return out


def _build_lag_frame(s: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": s})
    df["dow"] = df.index.dayofweek
    df["doy"] = df.index.dayofyear
    for lag in (1, 7, 14, 28):
        df[f"lag_{lag}"] = df["y"].shift(lag)
    for w in (7, 14):
        df[f"ma_{w}"] = df["y"].shift(1).rolling(w).mean()
    df = df.dropna()
    return df


def gbm_forecast(hist: pd.DataFrame, horizon_days: int) -> list[tuple[date, float]]:
    """GBM over lag + calendar features. Falls back to seasonal naive on tiny series."""
    from sklearn.ensemble import GradientBoostingRegressor

    s = _series(hist)
    if len(s) < 60:
        return seasonal_naive(hist, horizon_days)
    frame = _build_lag_frame(s)
    X = frame.drop(columns=["y"]).to_numpy()
    y = frame["y"].to_numpy()
    model = GradientBoostingRegressor(
        n_estimators=120, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X, y)
    out: list[tuple[date, float]] = []
    extended = s.copy()
    for i in range(horizon_days):
        next_date = extended.index[-1] + pd.Timedelta(days=1)
        row = {
            "dow": next_date.dayofweek,
            "doy": next_date.dayofyear,
            "lag_1": float(extended.iloc[-1]),
            "lag_7": float(extended.iloc[-7]) if len(extended) >= 7 else float(extended.iloc[-1]),
            "lag_14": float(extended.iloc[-14]) if len(extended) >= 14 else float(extended.iloc[-1]),
            "lag_28": float(extended.iloc[-28]) if len(extended) >= 28 else float(extended.iloc[-1]),
            "ma_7": float(extended.iloc[-7:].mean()),
            "ma_14": float(extended.iloc[-14:].mean()),
        }
        X_next = np.array([[row[c] for c in ("dow", "doy", "lag_1", "lag_7", "lag_14", "lag_28", "ma_7", "ma_14")]])
        yhat = float(max(0.0, model.predict(X_next)[0]))
        out.append((next_date.date(), yhat))
        extended = pd.concat([extended, pd.Series([yhat], index=[next_date])])
    return out


# --- evaluation metrics ----------------------------------------------------

def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    mask = denom > 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / denom[mask]))


def evaluate_series(hist: pd.DataFrame, horizon_days: int = 14) -> dict[str, Any]:
    """Temporal train/test split: last `horizon_days` are held out."""
    s = _series(hist)
    if len(s) < horizon_days + 30:
        return {"skipped": True, "reason": "series too short"}
    train = s.iloc[:-horizon_days]
    test = s.iloc[-horizon_days:]
    y_true = test.to_numpy()
    results = {}
    for name, fn in (
        ("seasonal_naive", seasonal_naive),
        ("ema", ema),
        ("gbm", gbm_forecast),
    ):
        preds = fn(hist.loc[hist.index <= train.index[-1].date()], horizon_days)
        y_pred = np.array([p for _, p in preds])
        results[name] = {
            "MAE": round(mae(y_true, y_pred), 3),
            "RMSE": round(rmse(y_true, y_pred), 3),
            "WAPE": round(wape(y_true, y_pred), 4),
            "sMAPE": round(smape(y_true, y_pred), 4),
        }
    return results
