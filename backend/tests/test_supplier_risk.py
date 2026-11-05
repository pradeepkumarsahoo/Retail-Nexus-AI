# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

import pandas as pd

from app.ml.supplier.risk import score


def _pos(otd_pattern: list[int]) -> pd.DataFrame:
    rows = []
    for i, slip in enumerate(otd_pattern):
        rows.append(
            {
                "po_id": f"PO{i}",
                "supplier_id": "SUP1",
                "product_id": "P",
                "store_id": "S",
                "units": 100,
                "order_date": f"2026-01-{(i % 28) + 1:02d}",
                "expected_delivery_date": "2026-02-01",
                "actual_delivery_date": f"2026-02-{1 + slip:02d}",
                "status": "DELIVERED",
            }
        )
    return pd.DataFrame(rows)


def test_reliable_supplier_low_risk():
    pos = _pos([0] * 10)
    r = score(pos, "SUP1")
    assert r.risk_score < 0.2
    assert r.risk_category == "LOW"


def test_flaky_supplier_high_risk():
    # Half the deliveries slip by 5 days — that's late.
    pos = _pos([0, 5, 0, 5, 0, 5, 0, 5, 0, 5])
    r = score(pos, "SUP1")
    assert r.risk_score > 0.3


def test_factor_contributions_sum_in_bounds():
    pos = _pos([0, 2, 5, 0, 10])
    r = score(pos, "SUP1")
    total = sum(f.contribution for f in r.factors)
    assert -0.01 <= total - r.risk_score <= 0.01
