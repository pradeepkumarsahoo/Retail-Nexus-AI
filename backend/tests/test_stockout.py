# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.ml.features import product_store_daily
from app.ml.stockout.model import predict


def _hist() -> pd.DataFrame:
    start = date(2026, 1, 1)
    rows = []
    for i in range(60):
        rows.append(
            {
                "sale_date": (start + timedelta(days=i)).isoformat(),
                "product_id": "P1",
                "store_id": "S1",
                "units_sold": 10,
                "revenue": 100.0,
                "promotion": False,
            }
        )
    return product_store_daily(pd.DataFrame(rows), "P1", "S1")


def test_predict_high_when_on_hand_low():
    hist = _hist()
    inv = {"on_hand_units": 5, "in_transit_units": 0}
    pred = predict(hist, inv, "P1", "S1", horizon_days=14, incoming_po_units=0, supplier_otd=0.7)
    assert pred.probability > 0.3
    assert pred.risk_category in ("MEDIUM", "HIGH", "CRITICAL")
    assert pred.predicted_stockout_date is not None


def test_predict_low_when_on_hand_high():
    hist = _hist()
    inv = {"on_hand_units": 500, "in_transit_units": 200}
    pred = predict(hist, inv, "P1", "S1", horizon_days=14, incoming_po_units=0, supplier_otd=0.95)
    assert pred.probability < 0.5
    assert pred.predicted_stockout_date is None


def test_predict_factors_populated():
    hist = _hist()
    pred = predict(hist, {"on_hand_units": 50, "in_transit_units": 0}, "P1", "S1")
    names = {f.name for f in pred.contributing_factors}
    assert {"days_of_supply", "demand_cv", "supplier_otd"}.issubset(names)
