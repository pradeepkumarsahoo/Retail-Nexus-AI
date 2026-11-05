# Author: Pradeep Sahoo — Retail Nexus AI
"""Stockout risk at product-store level.

Approach:
- Deterministic baseline — compute expected cumulative demand over horizon, compare to
  available inventory + expected deliveries. Return a probability using a logistic
  transform on `days_of_supply` and demand variability. Explainable, no training needed.
- Optional: a logistic regression trained on past windows of the labelled synthetic
  dataset. Compared against the baseline during evaluation.

The service layer calls `predict()` which returns a `StockoutPrediction` with
probability, risk category, main contributing factors and the suggested action.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.ml.features import days_of_supply, demand_features
from app.ml.forecasting.forecast import seasonal_naive


@dataclass
class StockoutFactor:
    name: str
    value: float
    contribution: float  # [-1, 1], positive = pushes probability up
    unit: str | None = None


@dataclass
class StockoutPrediction:
    product_id: str
    store_id: str
    horizon_days: int
    probability: float
    predicted_stockout_date: date | None
    risk_category: str
    contributing_factors: list[StockoutFactor]
    suggested_action: str
    data: dict[str, Any]


def _categorize(p: float) -> str:
    if p >= 0.75:
        return "CRITICAL"
    if p >= 0.5:
        return "HIGH"
    if p >= 0.25:
        return "MEDIUM"
    return "LOW"


def _suggested_action(prob: float, dos: float) -> str:
    if prob >= 0.75:
        return "EXPEDITE_PO" if dos < 2 else "TRANSFER_INVENTORY"
    if prob >= 0.5:
        return "TRANSFER_INVENTORY"
    if prob >= 0.25:
        return "INCREASE_REPLENISHMENT"
    return "MONITOR"


def predict(
    sales_history: pd.DataFrame,
    inventory_now: dict[str, Any],
    product_id: str,
    store_id: str,
    horizon_days: int = 14,
    incoming_po_units: int = 0,
    supplier_otd: float = 0.9,
) -> StockoutPrediction:
    """Baseline-first stockout risk, with GBM forecast when enough history exists."""
    feat = demand_features(sales_history)
    on_hand = float(inventory_now.get("on_hand_units", 0))
    in_transit = float(inventory_now.get("in_transit_units", 0))
    # Discount in-transit units by supplier OTD — if a supplier is unreliable, discount more.
    reliable_in_transit = in_transit * max(0.5, supplier_otd)
    available = on_hand + reliable_in_transit + incoming_po_units * max(0.5, supplier_otd)

    # Forecast over horizon. Default to the fast seasonal-naive baseline — callers
    # that explicitly want the GBM path call `gbm_forecast(...)` directly.
    preds = seasonal_naive(sales_history, horizon_days)
    forecast_vals = np.array([p for _, p in preds], dtype=float)
    cumulative = np.cumsum(forecast_vals)

    # Deterministic stockout day: first index where cumulative > available
    stockout_day: date | None = None
    for i, c in enumerate(cumulative):
        if c > available:
            stockout_day = preds[i][0]
            break

    dos = days_of_supply(on_hand, feat.mean_daily) if feat.mean_daily > 0 else 999.0
    # Logistic transform combining several explainable signals
    #   base z: 5 - dos (lower dos → higher)
    #   demand variability (CV) adds risk
    #   promotion days in last 14 adds risk
    #   supplier OTD subtracts risk
    z = (5.0 - dos) * 0.6
    z += feat.cv_daily * 1.5
    z += 0.1 * feat.promotion_days_14
    z -= (supplier_otd - 0.9) * 4.0
    # If a deterministic stockout exists inside horizon, push probability up
    if stockout_day is not None:
        days_to_stockout = (stockout_day - (preds[0][0] - timedelta(days=1))).days
        z += max(0.0, (horizon_days - days_to_stockout) / horizon_days) * 2.0
    # Clamp z before the exponential to avoid OverflowError on extreme inputs
    # (e.g. very low days-of-supply with imminent stockout).
    z = max(-50.0, min(50.0, z))
    prob = 1.0 / (1.0 + math.exp(-z))

    factors = [
        StockoutFactor("days_of_supply", round(dos, 2), -_clip((dos - 5) / 10)),
        StockoutFactor("demand_cv", round(feat.cv_daily, 3), _clip(feat.cv_daily)),
        StockoutFactor("supplier_otd", round(supplier_otd, 3), -_clip((supplier_otd - 0.8) * 3)),
        StockoutFactor(
            "recent_sales_14",
            round(feat.recent_sales_14, 2),
            _clip(feat.recent_sales_14 / max(1, feat.mean_daily * 14) - 1),
        ),
        StockoutFactor("in_transit", round(in_transit, 2), -_clip(in_transit / max(1, feat.mean_daily * 14))),
    ]
    data = {
        "on_hand_units": int(on_hand),
        "in_transit_units": int(in_transit),
        "incoming_po_units": int(incoming_po_units),
        "mean_daily_demand": round(feat.mean_daily, 3),
        "demand_cv": round(feat.cv_daily, 3),
        "forecast_horizon_units": [round(float(v), 2) for v in forecast_vals.tolist()],
    }
    return StockoutPrediction(
        product_id=product_id,
        store_id=store_id,
        horizon_days=horizon_days,
        probability=round(float(prob), 4),
        predicted_stockout_date=stockout_day,
        risk_category=_categorize(prob),
        contributing_factors=factors,
        suggested_action=_suggested_action(prob, dos),
        data=data,
    )


def _clip(v: float) -> float:
    return float(max(-1.0, min(1.0, v)))


# --- evaluation: compare baseline vs logistic regression ---------------------


def build_training_frame(
    sales: pd.DataFrame,
    inventory: pd.DataFrame,
    pos: pd.DataFrame,
    horizon_days: int = 7,
) -> pd.DataFrame:
    """Walk weekly snapshots, label stockout_within_horizon from sales data."""
    rows: list[dict[str, Any]] = []
    sales_g = sales.groupby(["product_id", "store_id"])
    inv_g = inventory.groupby(["product_id", "store_id"])
    for (pid, sid), inv_df in inv_g:
        inv_df = inv_df.sort_values("snapshot_date")
        try:
            s_hist_df = sales_g.get_group((pid, sid))
        except KeyError:
            continue
        s_hist_df = s_hist_df.copy()
        s_hist_df["sale_date"] = pd.to_datetime(s_hist_df["sale_date"]).dt.date
        s_hist_df = s_hist_df.sort_values("sale_date")
        for _, snap in inv_df.iterrows():
            snap_date = pd.to_datetime(snap["snapshot_date"]).date()
            on_hand = int(snap["on_hand_units"])
            in_transit = int(snap["in_transit_units"])
            window_hist = s_hist_df[s_hist_df["sale_date"] < snap_date].tail(28)
            if len(window_hist) < 14:
                continue
            future = s_hist_df[
                (s_hist_df["sale_date"] >= snap_date)
                & (s_hist_df["sale_date"] < snap_date + timedelta(days=horizon_days))
            ]
            future_units = int(future["units_sold"].sum())
            cum_demand_days = future.sort_values("sale_date")["units_sold"].cumsum().tolist()
            label = 1 if any(c > (on_hand + in_transit) for c in cum_demand_days) else 0
            mu = float(window_hist["units_sold"].mean())
            sd = float(window_hist["units_sold"].std(ddof=0)) if len(window_hist) > 1 else 0.0
            dos = (on_hand / mu) if mu > 0 else 999.0
            rows.append(
                {
                    "product_id": pid,
                    "store_id": sid,
                    "snapshot_date": snap_date,
                    "on_hand": on_hand,
                    "in_transit": in_transit,
                    "mean_daily": mu,
                    "std_daily": sd,
                    "cv": sd / mu if mu > 0 else 0.0,
                    "dos": min(dos, 365.0),
                    "future_units": future_units,
                    "stockout_within_horizon": label,
                }
            )
    return pd.DataFrame(rows)


def evaluate_models(frame: pd.DataFrame) -> dict[str, Any]:
    """Temporal split + logistic regression; return baseline vs LR metrics."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        average_precision_score,
        brier_score_loss,
        roc_auc_score,
    )

    if frame.empty:
        return {"skipped": True, "reason": "empty frame"}
    frame = frame.sort_values("snapshot_date").reset_index(drop=True)
    split = int(len(frame) * 0.75)
    train = frame.iloc[:split]
    test = frame.iloc[split:]
    feats = ["on_hand", "in_transit", "mean_daily", "std_daily", "cv", "dos"]
    if train["stockout_within_horizon"].sum() == 0 or test["stockout_within_horizon"].sum() == 0:
        return {"skipped": True, "reason": "no positives in train or test split"}
    X_train = train[feats].to_numpy()
    y_train = train["stockout_within_horizon"].to_numpy()
    X_test = test[feats].to_numpy()
    y_test = test["stockout_within_horizon"].to_numpy()

    # Baseline: 1 - dos/14 clipped
    baseline_prob = np.clip(1.0 - (test["dos"].to_numpy() / 14.0), 0.0, 1.0)
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_train, y_train)
    lr_prob = lr.predict_proba(X_test)[:, 1]

    def _m(name: str, prob: np.ndarray) -> dict[str, Any]:
        return {
            "model": name,
            "ROC_AUC": round(float(roc_auc_score(y_test, prob)), 4),
            "PR_AUC": round(float(average_precision_score(y_test, prob)), 4),
            "Brier": round(float(brier_score_loss(y_test, prob)), 4),
            "positives_in_test": int(y_test.sum()),
            "test_size": int(len(y_test)),
        }

    return {
        "features": feats,
        "baseline_dos": _m("baseline_dos", baseline_prob),
        "logistic_regression": _m("logistic_regression", lr_prob),
    }
