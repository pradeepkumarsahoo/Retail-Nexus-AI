# Author: Pradeep Sahoo — Retail Nexus AI
"""Supplier delay risk model.

Scoring:
- Deterministic score: weighted mix of (1 - OTD), normalized lead_time_variance,
  late_po_count/total_po_count, with explicit weights.
- Classifier: logistic regression on labelled late/not-late PO outcomes for
  held-out evaluation only (training uses historical PO slip > 2 days as positive).

Returns an interpretable risk score in [0, 1] with per-factor contributions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.ml.features import supplier_delivery_stats


@dataclass
class SupplierRiskFactor:
    name: str
    value: float
    weight: float
    contribution: float


@dataclass
class SupplierRiskResult:
    supplier_id: str
    risk_score: float
    risk_category: str
    factors: list[SupplierRiskFactor]
    stats: dict[str, Any]


_WEIGHTS = {
    "otd_gap": 0.5,
    "lt_variance_norm": 0.2,
    "recent_late_ratio": 0.3,
}


def _categorize(risk: float) -> str:
    if risk >= 0.6:
        return "HIGH"
    if risk >= 0.3:
        return "MEDIUM"
    return "LOW"


def score(pos: pd.DataFrame, supplier_id: str) -> SupplierRiskResult:
    stats = supplier_delivery_stats(pos, supplier_id)
    otd_gap = 1.0 - stats["on_time_delivery_pct"]
    lt_var_norm = min(1.0, stats["lead_time_variance"] / 50.0)
    recent_late_ratio = stats["late_po_count"] / max(1, stats["total_po_count"])
    components = {
        "otd_gap": otd_gap,
        "lt_variance_norm": lt_var_norm,
        "recent_late_ratio": recent_late_ratio,
    }
    risk = sum(_WEIGHTS[k] * components[k] for k in _WEIGHTS)
    risk = float(min(1.0, max(0.0, risk)))
    factors = [
        SupplierRiskFactor(
            name=k, value=round(components[k], 4), weight=_WEIGHTS[k],
            contribution=round(_WEIGHTS[k] * components[k], 4),
        )
        for k in _WEIGHTS
    ]
    return SupplierRiskResult(
        supplier_id=supplier_id, risk_score=round(risk, 4),
        risk_category=_categorize(risk), factors=factors, stats=stats,
    )


def evaluate(pos: pd.DataFrame) -> dict[str, Any]:
    """Predict PO-level late outcomes with logistic regression; compare to naive baseline."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

    delivered = pos[pos["status"] == "DELIVERED"].copy()
    if delivered.empty:
        return {"skipped": True, "reason": "no delivered POs"}
    delivered["expected_delivery_date"] = pd.to_datetime(delivered["expected_delivery_date"])
    delivered["actual_delivery_date"] = pd.to_datetime(delivered["actual_delivery_date"])
    delivered["order_date"] = pd.to_datetime(delivered["order_date"])
    delivered["slip"] = (delivered["actual_delivery_date"] - delivered["expected_delivery_date"]).dt.days
    delivered["lead_time"] = (delivered["actual_delivery_date"] - delivered["order_date"]).dt.days
    delivered["late"] = (delivered["slip"] > 2).astype(int)
    rows = []
    for _, po in delivered.sort_values("order_date").iterrows():
        prior = delivered[delivered["order_date"] < po["order_date"]]
        prior_sup = prior[prior["supplier_id"] == po["supplier_id"]]
        otd_prior = (prior_sup["slip"] <= 1).mean() if len(prior_sup) else 0.9
        rows.append({
            "late": int(po["late"]),
            "otd_prior": float(otd_prior),
            "nominal_lead_time": int(po["lead_time"]),
            "month": po["order_date"].month,
        })
    frame = pd.DataFrame(rows)
    if frame.empty or frame["late"].sum() == 0 or frame["late"].sum() == len(frame):
        return {"skipped": True, "reason": "no label variance"}
    split = int(len(frame) * 0.75)
    train, test = frame.iloc[:split], frame.iloc[split:]
    if train["late"].sum() == 0 or test["late"].sum() == 0:
        return {"skipped": True, "reason": "no positives in split"}
    X_tr = train[["otd_prior", "nominal_lead_time", "month"]].to_numpy()
    y_tr = train["late"].to_numpy()
    X_te = test[["otd_prior", "nominal_lead_time", "month"]].to_numpy()
    y_te = test["late"].to_numpy()
    baseline = 1.0 - test["otd_prior"].to_numpy()
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_tr, y_tr)
    lr_prob = lr.predict_proba(X_te)[:, 1]

    def _m(name: str, prob: np.ndarray) -> dict[str, Any]:
        return {
            "model": name,
            "ROC_AUC": round(float(roc_auc_score(y_te, prob)), 4),
            "PR_AUC": round(float(average_precision_score(y_te, prob)), 4),
            "Brier": round(float(brier_score_loss(y_te, prob)), 4),
        }
    return {
        "features": ["otd_prior", "nominal_lead_time", "month"],
        "baseline_1_minus_otd": _m("baseline_1_minus_otd", baseline),
        "logistic_regression": _m("logistic_regression", lr_prob),
        "n_test": len(y_te),
    }
