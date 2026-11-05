# Author: Pradeep Sahoo — Retail Nexus AI
"""Unified Exception Detection Engine.

Sweeps the latest data for 11 exception categories and persists
Exception rows with evidence, risk score, estimated impact and workflow hint.

Risk score formula (transparent):

    risk_score = clamp(
        0.35 * norm_severity_signal
      + 0.25 * recency
      + 0.20 * data_coverage
      + 0.15 * financial_exposure_norm
      + 0.05 * cross_signal_bonus,
        0, 1
    )

Each exception also carries a `risk_score_components` block for inspection.
"""

from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.domain.enums import ExceptionCategory, ExceptionStatus, Severity
from app.ml.anomaly.detector import detect as detect_anomalies
from app.ml.features import (
    days_of_supply,
    demand_features,
    inventory_snapshot_current,
    supplier_delivery_stats,
)
from app.ml.stockout.model import predict as predict_stockout
from app.ml.supplier.risk import score as score_supplier_risk
from app.models import orm
from app.repositories import frames as fr

RISK_WEIGHTS = {
    "severity_signal": 0.35,
    "recency": 0.25,
    "coverage": 0.20,
    "financial": 0.15,
    "cross_signal_bonus": 0.05,
}


def _sev(risk: float) -> Severity:
    if risk >= 0.75:
        return Severity.CRITICAL
    if risk >= 0.5:
        return Severity.HIGH
    if risk >= 0.25:
        return Severity.MEDIUM
    return Severity.LOW


def _risk(
    severity_signal: float, recency: float, coverage: float, financial: float, cross_signal_bonus: float = 0.0
) -> tuple[float, dict[str, float]]:
    severity_signal = _clip01(severity_signal)
    recency = _clip01(recency)
    coverage = _clip01(coverage)
    financial = _clip01(financial)
    bonus = _clip01(cross_signal_bonus)
    components = {
        "severity_signal": round(severity_signal, 3),
        "recency": round(recency, 3),
        "coverage": round(coverage, 3),
        "financial": round(financial, 3),
        "cross_signal_bonus": round(bonus, 3),
    }
    score = sum(RISK_WEIGHTS[k] * v for k, v in components.items())
    return round(_clip01(score), 4), components


def _clip01(v: float) -> float:
    return float(max(0.0, min(1.0, v)))


def _new_eid() -> str:
    return f"EXC-{uuid.uuid4().hex[:12].upper()}"


def _save(session: Session, exc: orm.Exception_) -> None:
    session.add(exc)


def _recency(ref_day: date, event_day: date, window_days: int = 30) -> float:
    delta = max(0, (ref_day - event_day).days)
    return max(0.0, 1.0 - (delta / window_days))


def _snapshot_date(inv: pd.DataFrame) -> date:
    if inv.empty:
        return date.today()
    return pd.to_datetime(inv["snapshot_date"].max()).date()


def _p_s_sales(sales: pd.DataFrame, pid: str, sid: str) -> pd.DataFrame:
    from app.ml.features import product_store_daily

    return product_store_daily(sales, pid, sid)


def detect_all(session: Session, horizon_days: int = 14) -> list[orm.Exception_]:
    """Full sweep; returns the list of created Exception rows (also persisted to DB)."""
    sales = fr.sales_frame(session)
    inv = fr.inventory_frame(session)
    pos = fr.po_frame(session)
    products = fr.product_dict(session)
    stores = fr.store_dict(session)
    suppliers = fr.supplier_dict(session)

    if sales.empty or inv.empty:
        return []

    ref_day = _snapshot_date(inv)
    results: list[orm.Exception_] = []

    # ---- Stockout risk (per product-store, only recent/active ones) --------
    # Iterate the Cartesian product of products × stores that have *any* history.
    for pid, pinfo in products.items():
        for sid, _sinfo in stores.items():
            hist = _p_s_sales(sales, pid, sid)
            if hist.empty or len(hist) < 14:
                continue
            inv_now = inventory_snapshot_current(inv, pid, sid)
            incoming = int(
                pos[(pos["product_id"] == pid) & (pos["store_id"] == sid) & (pos["status"] == "OPEN")][
                    "units"
                ].sum()
            )
            # Pick supplier OTD by product's primary supplier (use best eligible by eligible+count)
            sp_df = fr.supplier_product_frame(session)
            sup_ids = sp_df[(sp_df["product_id"] == pid) & (sp_df["eligible"])]["supplier_id"].tolist()
            otd_vals = []
            for s_id in sup_ids:
                stats = supplier_delivery_stats(pos, s_id)
                otd_vals.append(stats["on_time_delivery_pct"])
            otd = float(np.mean(otd_vals)) if otd_vals else 0.9
            pred = predict_stockout(
                hist,
                inv_now,
                pid,
                sid,
                horizon_days=horizon_days,
                incoming_po_units=incoming,
                supplier_otd=otd,
            )
            if pred.probability >= 0.3:
                feat = demand_features(hist)
                mean_daily = feat.mean_daily
                est_impact = pred.probability * mean_daily * horizon_days * pinfo["unit_price"]
                severity_signal = pred.probability
                recency = 1.0
                coverage = min(1.0, len(hist) / 90.0)
                financial = min(1.0, est_impact / 10000.0)
                cross = 0.3 if otd < 0.8 else 0.0
                risk, components = _risk(severity_signal, recency, coverage, financial, cross)
                evidence = {
                    "probability": pred.probability,
                    "predicted_stockout_date": pred.predicted_stockout_date.isoformat()
                    if pred.predicted_stockout_date
                    else None,
                    "risk_category": pred.risk_category,
                    "contributing_factors": [f.__dict__ for f in pred.contributing_factors],
                    "data": pred.data,
                    "suggested_action": pred.suggested_action,
                    "supplier_otd_avg": round(otd, 3),
                    "risk_score_components": components,
                }
                exc = orm.Exception_(
                    exception_id=_new_eid(),
                    category=ExceptionCategory.STOCKOUT_RISK.value,
                    product_id=pid,
                    store_id=sid,
                    supplier_id=None,
                    severity=_sev(risk).value,
                    risk_score=risk,
                    evidence=evidence,
                    estimated_impact_usd=round(est_impact, 2),
                    status=ExceptionStatus.OPEN.value,
                    workflow_hint="investigate_inventory_and_supplier",
                )
                _save(session, exc)
                results.append(exc)

            # Low days-of-supply shows up as its own exception when DoS < 3 even if the model
            # does not call stockout — this covers edge cases with uneven variance.
            if inv_now["on_hand_units"] <= 1 and demand_features(hist).mean_daily >= 1:
                dos = days_of_supply(inv_now["on_hand_units"], demand_features(hist).mean_daily)
                severity_signal = 1.0
                recency = 1.0
                coverage = 0.7
                financial = min(1.0, pinfo["unit_price"] * demand_features(hist).mean_daily * 7 / 5000.0)
                risk, components = _risk(severity_signal, recency, coverage, financial)
                exc = orm.Exception_(
                    exception_id=_new_eid(),
                    category=ExceptionCategory.LOW_DAYS_OF_SUPPLY.value,
                    product_id=pid,
                    store_id=sid,
                    supplier_id=None,
                    severity=_sev(risk).value,
                    risk_score=risk,
                    evidence={
                        "days_of_supply": round(dos, 2),
                        "on_hand": inv_now["on_hand_units"],
                        "risk_score_components": components,
                    },
                    estimated_impact_usd=round(pinfo["unit_price"] * demand_features(hist).mean_daily * 7, 2),
                    status=ExceptionStatus.OPEN.value,
                    workflow_hint="investigate_inventory",
                )
                _save(session, exc)
                results.append(exc)

    # ---- Demand anomalies (last 14 days only) ------------------------------
    for pid, pinfo in products.items():
        for sid, _sinfo in stores.items():
            hist = _p_s_sales(sales, pid, sid)
            if hist.empty:
                continue
            anoms = detect_anomalies(hist.tail(90), z_threshold=2.5)
            recent = [a for a in anoms if (ref_day - a.date).days <= 14]
            if not recent:
                continue
            latest = sorted(recent, key=lambda x: x.date)[-1]
            cat = (
                ExceptionCategory.DEMAND_SPIKE
                if latest.kind == "DEMAND_SPIKE"
                else ExceptionCategory.DEMAND_DECLINE
            )
            severity_signal = min(1.0, abs(latest.z_score) / 5.0)
            recency = _recency(ref_day, latest.date, 14)
            coverage = min(1.0, len(hist) / 90.0)
            feat = demand_features(hist)
            est_impact = (
                feat.mean_daily
                * 7
                * pinfo["unit_price"]
                * (0.3 if cat == ExceptionCategory.DEMAND_DECLINE else 0.1)
            )
            financial = min(1.0, est_impact / 5000.0)
            risk, components = _risk(severity_signal, recency, coverage, financial)
            exc = orm.Exception_(
                exception_id=_new_eid(),
                category=cat.value,
                product_id=pid,
                store_id=sid,
                supplier_id=None,
                severity=_sev(risk).value,
                risk_score=risk,
                evidence={
                    "z_score": latest.z_score,
                    "day": latest.date.isoformat(),
                    "units": latest.units,
                    "kind": latest.kind,
                    "risk_score_components": components,
                },
                estimated_impact_usd=round(est_impact, 2),
                status=ExceptionStatus.OPEN.value,
                workflow_hint="investigate_demand",
            )
            _save(session, exc)
            results.append(exc)

    # ---- Supplier delay / capacity -----------------------------------------
    for sup_id, sup in suppliers.items():
        risk_result = score_supplier_risk(pos, sup_id)
        if risk_result.risk_score >= 0.3:
            severity_signal = risk_result.risk_score
            recency = 1.0
            coverage = min(1.0, risk_result.stats["total_po_count"] / 20.0)
            financial = min(1.0, risk_result.stats["late_po_count"] * 500.0 / 10000.0)
            risk, components = _risk(severity_signal, recency, coverage, financial)
            exc = orm.Exception_(
                exception_id=_new_eid(),
                category=ExceptionCategory.SUPPLIER_DELAY.value,
                product_id=None,
                store_id=None,
                supplier_id=sup_id,
                severity=_sev(risk).value,
                risk_score=risk,
                evidence={
                    "supplier_name": sup["name"],
                    "stats": risk_result.stats,
                    "factors": [f.__dict__ for f in risk_result.factors],
                    "risk_score_components": components,
                },
                estimated_impact_usd=round(risk_result.stats["late_po_count"] * 2500.0, 2),
                status=ExceptionStatus.OPEN.value,
                workflow_hint="investigate_supplier",
            )
            _save(session, exc)
            results.append(exc)

    # ---- Excess & aging inventory ------------------------------------------
    for pid, pinfo in products.items():
        for sid, _sinfo in stores.items():
            inv_now = inventory_snapshot_current(inv, pid, sid)
            hist = _p_s_sales(sales, pid, sid)
            if hist.empty or inv_now["on_hand_units"] <= 0:
                continue
            feat = demand_features(hist)
            if feat.mean_daily <= 0:
                continue
            dos = days_of_supply(inv_now["on_hand_units"], feat.mean_daily)
            shelf = pinfo.get("shelf_life_days") or 999
            if dos > 90:
                # Likely excess
                severity_signal = min(1.0, (dos - 90) / 90)
                recency = 1.0
                coverage = min(1.0, len(hist) / 90.0)
                financial = min(1.0, inv_now["on_hand_units"] * pinfo["unit_cost"] / 20000.0)
                risk, components = _risk(severity_signal, recency, coverage, financial)
                cat = (
                    ExceptionCategory.AGING_INVENTORY
                    if shelf and dos > shelf * 0.5
                    else ExceptionCategory.EXCESS_INVENTORY
                )
                exc = orm.Exception_(
                    exception_id=_new_eid(),
                    category=cat.value,
                    product_id=pid,
                    store_id=sid,
                    supplier_id=None,
                    severity=_sev(risk).value,
                    risk_score=risk,
                    evidence={
                        "days_of_supply": round(dos, 2),
                        "on_hand": inv_now["on_hand_units"],
                        "shelf_life_days": shelf,
                        "risk_score_components": components,
                    },
                    estimated_impact_usd=round(inv_now["on_hand_units"] * pinfo["unit_cost"] * 0.1, 2),
                    status=ExceptionStatus.OPEN.value,
                    workflow_hint="investigate_inventory",
                )
                _save(session, exc)
                results.append(exc)

    session.flush()
    return results
