# Author: Pradeep Sahoo — Retail Nexus AI
"""Deterministic what-if simulation engine.

Scenarios:
  BASELINE               — no intervention.
  EXPEDITE               — bring in-transit units in `expedite_days` sooner at `expedite_cost_per_unit`.
  TRANSFER               — move `transfer_units` from another store (free inventory, transfer cost per unit).
  SWITCH_SUPPLIER        — reorder from alt supplier with different lead time and unit cost.
  INCREASE_REPLENISHMENT — add `extra_units` to the horizon at marginal unit cost.

All outputs are produced by explicit formulas and labelled with the assumptions used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.ml.forecasting.forecast import seasonal_naive


@dataclass
class ScenarioResult:
    scenario: str
    projected_inventory_units: int
    expected_stockout_units: int
    expected_lost_sales_units: int
    revenue_exposure_usd: float
    intervention_cost_usd: float
    net_benefit_usd: float
    assumptions: list[str]
    constraints: list[str]


def _project(
    forecast: list[float],
    starting_inventory: float,
    extra_deliveries_by_day: list[float] | None = None,
) -> tuple[int, int, int]:
    """Walk day-by-day: subtract demand, add deliveries, track stockout units."""
    inv = starting_inventory
    stockout = 0
    deliveries = extra_deliveries_by_day or [0.0] * len(forecast)
    for i, mu in enumerate(forecast):
        inv += deliveries[i]
        if inv >= mu:
            inv -= mu
        else:
            stockout += int(mu - inv)
            inv = 0
    projected = max(0, int(inv))
    expected_lost_sales = stockout  # 1:1 under the simplifying assumption that unmet demand is lost
    return projected, stockout, expected_lost_sales


def run(
    exception_payload: dict[str, Any],
    scenarios: list[dict[str, Any]],
    sales_history: pd.DataFrame,
    inventory_now: dict[str, Any],
    unit_price: float,
    unit_cost: float,
    horizon_days: int = 14,
) -> list[ScenarioResult]:
    """Run each scenario and return a comparable list."""
    forecast = [v for _, v in seasonal_naive(sales_history, horizon_days)]
    on_hand = float(inventory_now.get("on_hand_units", 0))
    in_transit = float(inventory_now.get("in_transit_units", 0))
    results: list[ScenarioResult] = []

    for sc in scenarios:
        name = sc["name"].upper()
        params = sc.get("params", {})
        assumptions = [
            f"Horizon = {horizon_days} days",
            "Daily forecast from seasonal-naive baseline over the recent sales window.",
            f"Unit price = ${unit_price:.2f}, unit cost = ${unit_cost:.2f}.",
            "Lost sales are assumed 1:1 for unmet demand units.",
        ]
        constraints: list[str] = []
        extra_deliveries = [0.0] * horizon_days
        intervention_cost = 0.0

        if name == "BASELINE":
            # In-transit arrives at `in_transit_days` default: distribute uniformly up to lead_time.
            lt = int(params.get("in_transit_arrival_day", min(horizon_days - 1, 7)))
            if in_transit > 0 and 0 <= lt < horizon_days:
                extra_deliveries[lt] += in_transit
            assumptions.append(f"In-transit arrival modelled on day {lt}.")
        elif name == "EXPEDITE":
            days = int(params.get("expedite_arrival_day", 2))
            cost_per_unit = float(params.get("expedite_cost_per_unit", unit_cost * 0.15))
            if in_transit > 0 and 0 <= days < horizon_days:
                extra_deliveries[days] += in_transit
            intervention_cost = in_transit * cost_per_unit
            assumptions.append(f"Expedited {int(in_transit)} in-transit units to arrive on day {days}.")
            assumptions.append(f"Expedite cost = ${cost_per_unit:.2f}/unit.")
        elif name == "TRANSFER":
            transfer_units = int(params.get("transfer_units", 0))
            arrive_day = int(params.get("arrival_day", 1))
            cost_per_unit = float(params.get("transfer_cost_per_unit", unit_cost * 0.08))
            if transfer_units > 0 and 0 <= arrive_day < horizon_days:
                extra_deliveries[arrive_day] += transfer_units
            intervention_cost = transfer_units * cost_per_unit
            assumptions.append(f"Transferring {transfer_units} units arriving on day {arrive_day}.")
            assumptions.append(f"Transfer cost = ${cost_per_unit:.2f}/unit.")
            if transfer_units <= 0:
                constraints.append("No eligible transfer source identified.")
        elif name == "SWITCH_SUPPLIER":
            alt_units = int(params.get("units", 0))
            lead = int(params.get("alt_lead_time_days", 5))
            alt_unit_cost = float(params.get("alt_unit_cost", unit_cost * 1.1))
            if alt_units > 0 and 0 <= lead < horizon_days:
                extra_deliveries[lead] += alt_units
            delta_cost = (alt_unit_cost - unit_cost) * alt_units
            intervention_cost = max(0.0, delta_cost)
            assumptions.append(f"Alt supplier delivery of {alt_units} units on day {lead}.")
            assumptions.append(f"Alt supplier cost delta = ${delta_cost:.2f}.")
        elif name == "INCREASE_REPLENISHMENT":
            extra_units = int(params.get("extra_units", 0))
            arrive_day = int(params.get("arrival_day", 7))
            cost_per_unit = float(params.get("marginal_cost_per_unit", unit_cost))
            if extra_units > 0 and 0 <= arrive_day < horizon_days:
                extra_deliveries[arrive_day] += extra_units
            intervention_cost = extra_units * cost_per_unit
            assumptions.append(f"Added replenishment of {extra_units} units on day {arrive_day}.")
        else:
            constraints.append(f"Unknown scenario name: {name}.")

        projected, stockout, lost = _project(forecast, on_hand, extra_deliveries)
        revenue_exposure = round(lost * unit_price, 2)
        net = round(-revenue_exposure - intervention_cost, 2)  # negative = loss
        # Benefit vs baseline is computed by the caller comparing to BASELINE result.
        results.append(
            ScenarioResult(
                scenario=name,
                projected_inventory_units=projected,
                expected_stockout_units=stockout,
                expected_lost_sales_units=lost,
                revenue_exposure_usd=revenue_exposure,
                intervention_cost_usd=round(intervention_cost, 2),
                net_benefit_usd=net,
                assumptions=assumptions,
                constraints=constraints,
            )
        )
    # Compute net benefit vs baseline, in-place
    baseline = next((r for r in results if r.scenario == "BASELINE"), None)
    if baseline:
        for r in results:
            if r.scenario == "BASELINE":
                continue
            # Benefit = (baseline revenue exposure - this exposure) - intervention cost
            r.net_benefit_usd = round(
                (baseline.revenue_exposure_usd - r.revenue_exposure_usd) - r.intervention_cost_usd, 2
            )
    return results
