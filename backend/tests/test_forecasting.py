# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd

from app.ml.forecasting.forecast import ema, evaluate_series, mae, rmse, seasonal_naive, smape, wape
from app.ml.features import product_store_daily
import numpy as np


def _hist(days: int = 90) -> pd.DataFrame:
    start = date(2026, 1, 1)
    rows = []
    for i in range(days):
        units = 10 + (i % 7) + (3 if (i % 30) < 5 else 0)
        rows.append({"sale_date": (start + timedelta(days=i)).isoformat(),
                     "product_id": "P1", "store_id": "S1",
                     "units_sold": units, "revenue": 10.0 * units, "promotion": False})
    return product_store_daily(pd.DataFrame(rows), "P1", "S1")


def test_seasonal_naive_cycles():
    hist = _hist(14)
    preds = seasonal_naive(hist, 7)
    assert len(preds) == 7
    assert all(v >= 0 for _, v in preds)


def test_ema_nonempty():
    hist = _hist(30)
    preds = ema(hist, 7)
    assert len(preds) == 7


def test_metrics_boundaries():
    y = np.array([10.0, 10.0, 10.0])
    yhat = np.array([10.0, 10.0, 10.0])
    assert mae(y, yhat) == 0
    assert rmse(y, yhat) == 0
    assert wape(y, yhat) == 0
    assert smape(y, yhat) == 0


def test_evaluate_series_returns_all_models():
    hist = _hist(90)
    res = evaluate_series(hist, horizon_days=14)
    assert "seasonal_naive" in res
    assert "ema" in res
    assert "gbm" in res
    for m, metrics in res.items():
        assert {"MAE", "RMSE", "WAPE", "sMAPE"}.issubset(metrics.keys())
