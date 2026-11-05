# Author: Pradeep Sahoo — Retail Nexus AI
"""Scenario simulator — deterministic given identical inputs."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from app.ml.features import product_store_daily
from app.simulation.simulator import run


def _hist() -> pd.DataFrame:
    start = date(2026, 1, 1)
    rows = []
    for i in range(45):
        rows.append(
            {
                "sale_date": (start + timedelta(days=i)).isoformat(),
                "product_id": "P1",
                "store_id": "S1",
                "units_sold": 15,
                "revenue": 150.0,
                "promotion": False,
            }
        )
    return product_store_daily(pd.DataFrame(rows), "P1", "S1")


def _call():
    return run(
        exception_payload={},
        scenarios=[
            {"name": "BASELINE"},
            {"name": "EXPEDITE", "params": {"expedite_arrival_day": 2}},
            {"name": "TRANSFER", "params": {"transfer_units": 100, "arrival_day": 1}},
        ],
        sales_history=_hist(),
        inventory_now={"on_hand_units": 50, "in_transit_units": 100},
        unit_price=10.0,
        unit_cost=4.0,
        horizon_days=14,
    )


def test_simulator_deterministic():
    a = _call()
    b = _call()
    for x, y in zip(a, b, strict=False):
        assert x.scenario == y.scenario
        assert x.projected_inventory_units == y.projected_inventory_units
        assert x.expected_stockout_units == y.expected_stockout_units
        assert x.revenue_exposure_usd == y.revenue_exposure_usd


def test_transfer_reduces_stockout_vs_baseline():
    outcomes = {o.scenario: o for o in _call()}
    assert outcomes["TRANSFER"].expected_stockout_units <= outcomes["BASELINE"].expected_stockout_units


def test_net_benefit_vs_baseline():
    outcomes = {o.scenario: o for o in _call()}
    baseline = outcomes["BASELINE"]
    expedite = outcomes["EXPEDITE"]
    expected = round(
        (baseline.revenue_exposure_usd - expedite.revenue_exposure_usd) - expedite.intervention_cost_usd, 2
    )
    assert expedite.net_benefit_usd == expected
