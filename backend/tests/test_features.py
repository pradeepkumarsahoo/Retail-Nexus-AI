# Author: Pradeep Sahoo — Retail Nexus AI
"""Unit tests for feature engineering."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.ml.features import (
    days_of_supply,
    demand_features,
    product_store_daily,
    supplier_delivery_stats,
)


def _make_sales(days: int = 60, pid="P1", sid="S1") -> pd.DataFrame:
    rows = []
    start = date(2026, 1, 1)
    for i in range(days):
        rows.append(
            {
                "sale_date": (start + timedelta(days=i)).isoformat(),
                "product_id": pid,
                "store_id": sid,
                "units_sold": 10 + (i % 7),
                "revenue": 100.0,
                "promotion": False,
            }
        )
    return pd.DataFrame(rows)


def test_product_store_daily_reindexes_missing_days():
    df = _make_sales(days=30)
    # drop one day — should reappear as 0 after reindex
    df = df.drop(index=5).reset_index(drop=True)
    out = product_store_daily(df, "P1", "S1")
    assert len(out) == 30  # reindexed to full span
    assert int(out["units_sold"].sum()) > 0


def test_demand_features_core_values():
    df = _make_sales(days=28)
    hist = product_store_daily(df, "P1", "S1")
    feat = demand_features(hist)
    assert feat.mean_daily > 0
    assert 0 <= feat.cv_daily <= 1
    assert len(feat.weekday_profile) == 7
    assert feat.recent_sales_7 > 0


def test_days_of_supply():
    assert days_of_supply(100, 10) == 10
    assert days_of_supply(0, 10) == 0
    assert days_of_supply(10, 0) == float("inf")


def test_supplier_delivery_stats_empty():
    stats = supplier_delivery_stats(pd.DataFrame(), "SUP1")
    assert stats["on_time_delivery_pct"] == 0.0
    assert stats["total_po_count"] == 0


def test_supplier_delivery_stats_delivered():
    pos = pd.DataFrame(
        [
            {
                "po_id": "P1",
                "supplier_id": "SUP1",
                "product_id": "P",
                "store_id": "S",
                "units": 10,
                "order_date": "2026-01-01",
                "expected_delivery_date": "2026-01-10",
                "actual_delivery_date": "2026-01-11",  # 1 day slip → still on-time
                "status": "DELIVERED",
            },
            {
                "po_id": "P2",
                "supplier_id": "SUP1",
                "product_id": "P",
                "store_id": "S",
                "units": 10,
                "order_date": "2026-02-01",
                "expected_delivery_date": "2026-02-10",
                "actual_delivery_date": "2026-02-20",  # 10 day slip — late
                "status": "DELIVERED",
            },
        ]
    )
    stats = supplier_delivery_stats(pos, "SUP1")
    assert stats["total_po_count"] == 2
    assert stats["on_time_delivery_pct"] == 0.5
    assert stats["late_po_count"] == 1
