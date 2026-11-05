# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.ml.anomaly.detector import detect
from app.ml.features import demand_features, product_store_daily
from app.ml.forecasting.forecast import gbm_forecast, seasonal_naive
from app.ml.stockout.model import predict as predict_stockout
from app.models import orm
from app.repositories import frames as fr
from app.schemas.common import (
    DashboardSummary,
    ForecastPoint,
    ForecastResponse,
    StockoutRiskResponse,
    EvidenceItem,
)
from app.security.auth import User, current_user

router = APIRouter()


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(session: Session = Depends(get_session), user: User = Depends(current_user)) -> DashboardSummary:
    active = session.execute(select(orm.Exception_).where(orm.Exception_.status.in_(("OPEN", "INVESTIGATING", "RECOMMENDATION_READY")))).scalars().all()
    by_sev: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    high_or_crit = 0
    revenue_exposure = 0.0
    products_at_risk: set[str] = set()
    suppliers_at_risk: set[str] = set()
    for e in active:
        by_sev[e.severity] = by_sev.get(e.severity, 0) + 1
        by_cat[e.category] = by_cat.get(e.category, 0) + 1
        if e.severity in ("HIGH", "CRITICAL"):
            high_or_crit += 1
        revenue_exposure += float(e.estimated_impact_usd or 0)
        if e.category in ("STOCKOUT_RISK", "LOW_DAYS_OF_SUPPLY") and e.product_id:
            products_at_risk.add(e.product_id)
        if e.category in ("SUPPLIER_DELAY", "SUPPLIER_CAPACITY") and e.supplier_id:
            suppliers_at_risk.add(e.supplier_id)
    pending = session.execute(
        select(func.count()).select_from(orm.Recommendation).where(orm.Recommendation.status == "PENDING_APPROVAL")
    ).scalar() or 0
    # Trend last 14 days (bucketed by date)
    trend: list[dict[str, Any]] = []
    today = datetime.utcnow().date()
    rows = session.execute(select(orm.Exception_.detected_at, orm.Exception_.severity)).all()
    by_day: dict[str, dict[str, int]] = {}
    for det, sev in rows:
        d = (det.date() if hasattr(det, "date") else det)
        if (today - d).days > 13:
            continue
        key = d.isoformat()
        by_day.setdefault(key, {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0})
        by_day[key][sev] = by_day[key].get(sev, 0) + 1
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        counts = by_day.get(key, {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0})
        trend.append({"date": key, **counts, "total": sum(counts.values())})

    return DashboardSummary(
        active_exceptions=len(active),
        high_or_critical=high_or_crit,
        products_at_stockout_risk=len(products_at_risk),
        suppliers_at_risk=len(suppliers_at_risk),
        estimated_revenue_exposure_usd=round(revenue_exposure, 2),
        pending_approvals=int(pending),
        exceptions_by_category=by_cat,
        exceptions_by_severity=by_sev,
        trend_last_14_days=trend,
    )


@router.get("/analytics/demand", response_model=ForecastResponse)
def analytics_demand(
    product_id: str = Query(...),
    store_id: str = Query(...),
    horizon_days: int = Query(14, ge=1, le=30),
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> ForecastResponse:
    sales = fr.sales_frame(session)
    hist = product_store_daily(sales, product_id, store_id)
    if hist.empty:
        raise HTTPException(status_code=404, detail="No sales history for product-store")
    model = "gbm" if len(hist) >= 60 else "seasonal_naive"
    preds = gbm_forecast(hist, horizon_days) if model == "gbm" else seasonal_naive(hist, horizon_days)
    recent = hist.tail(30).reset_index().rename(columns={"index": "sale_date"})
    recent_json = [{"date": d["sale_date"].isoformat() if hasattr(d["sale_date"], "isoformat") else str(d["sale_date"]),
                    "units": int(d["units_sold"]), "promotion": bool(d["promotion"])} for d in recent.to_dict("records")]
    return ForecastResponse(
        product_id=product_id, store_id=store_id, model=model, horizon_days=horizon_days,
        forecast=[ForecastPoint(date=d, forecast_units=round(float(v), 3)) for d, v in preds],
        recent_sales=recent_json,
    )


@router.get("/analytics/stockout-risk", response_model=StockoutRiskResponse)
def analytics_stockout(
    product_id: str = Query(...),
    store_id: str = Query(...),
    horizon_days: int = Query(14, ge=1, le=30),
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> StockoutRiskResponse:
    from app.ml.features import inventory_snapshot_current, supplier_delivery_stats
    import numpy as np

    sales = fr.sales_frame(session)
    inv = fr.inventory_frame(session)
    pos = fr.po_frame(session)
    sp = fr.supplier_product_frame(session)
    hist = product_store_daily(sales, product_id, store_id)
    if hist.empty:
        raise HTTPException(status_code=404, detail="No sales history for product-store")
    inv_now = inventory_snapshot_current(inv, product_id, store_id)
    incoming = int(pos[(pos["product_id"] == product_id) & (pos["store_id"] == store_id) & (pos["status"] == "OPEN")]["units"].sum())
    sup_ids = sp[(sp["product_id"] == product_id) & sp["eligible"]]["supplier_id"].tolist()
    otd = float(np.mean([supplier_delivery_stats(pos, s)["on_time_delivery_pct"] for s in sup_ids])) if sup_ids else 0.9
    pred = predict_stockout(hist, inv_now, product_id, store_id, horizon_days=horizon_days,
                            incoming_po_units=incoming, supplier_otd=otd)
    return StockoutRiskResponse(
        product_id=pred.product_id, store_id=pred.store_id, horizon_days=pred.horizon_days,
        probability=pred.probability, predicted_stockout_date=pred.predicted_stockout_date,
        risk_category=pred.risk_category,
        contributing_factors=[EvidenceItem(source="stockout_model", metric=f.name, value=f.value,
                                           notes=f"contribution={f.contribution}") for f in pred.contributing_factors],
        suggested_action=pred.suggested_action,  # type: ignore[arg-type]
        data=pred.data,
    )
