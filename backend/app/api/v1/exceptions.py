# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.events.bus import publish
from app.models import orm
from app.orchestration.supervisor import investigate
from app.schemas.common import ExceptionOut, RecommendationOut
from app.security.auth import User, current_user
from app.security.rate_limit import rate_limited
from app.services.exceptions_engine import detect_all

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


@router.get("", response_model=dict)
def list_exceptions(
    status: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    store_id: str | None = None,
    product_id: str | None = None,
    supplier_id: str | None = None,
    min_risk: float | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    stmt = select(orm.Exception_)
    if status:
        stmt = stmt.where(orm.Exception_.status == status)
    if category:
        stmt = stmt.where(orm.Exception_.category == category)
    if severity:
        stmt = stmt.where(orm.Exception_.severity == severity)
    if store_id:
        stmt = stmt.where(orm.Exception_.store_id == store_id)
    if product_id:
        stmt = stmt.where(orm.Exception_.product_id == product_id)
    if supplier_id:
        stmt = stmt.where(orm.Exception_.supplier_id == supplier_id)
    if min_risk is not None:
        stmt = stmt.where(orm.Exception_.risk_score >= min_risk)
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = (
        stmt.order_by(orm.Exception_.risk_score.desc(), orm.Exception_.detected_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()
    return {
        "page": {"total": int(total), "offset": offset, "limit": limit},
        "items": [ExceptionOut.model_validate(r).model_dump() for r in rows],
    }


@router.get("/{exception_id}", response_model=ExceptionOut)
def get_exception(
    exception_id: str, session: Session = Depends(get_session), user: User = Depends(current_user)
) -> ExceptionOut:
    row = session.get(orm.Exception_, exception_id)
    if not row:
        raise HTTPException(status_code=404, detail="Exception not found")
    return ExceptionOut.model_validate(row)


@router.post("/detect", dependencies=[Depends(rate_limited(limit_per_minute=30))])
def run_detection(
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    created = detect_all(session)
    for exc in created:
        publish(
            session,
            event_type="StockoutRiskDetected" if exc.category == "STOCKOUT_RISK" else exc.category,
            payload={
                "exception_id": exc.exception_id,
                "category": exc.category,
                "risk_score": exc.risk_score,
            },
        )
    session.commit()
    return {"created": len(created), "exception_ids": [e.exception_id for e in created]}


@router.post("/{exception_id}/investigate", dependencies=[Depends(rate_limited(limit_per_minute=60))])
def investigate_exception(
    exception_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    row = session.get(orm.Exception_, exception_id)
    if not row:
        raise HTTPException(status_code=404, detail="Exception not found")
    state = investigate(session, row)
    session.commit()
    # Load created recommendations to return
    recs = (
        session.execute(
            select(orm.Recommendation)
            .where(orm.Recommendation.exception_id == exception_id)
            .order_by(orm.Recommendation.created_at.desc())
        )
        .scalars()
        .all()
    )
    return {
        "exception_id": exception_id,
        "run": {
            "provider": state.provider,
            "model": state.model,
            "tokens_in": state.tokens_in,
            "tokens_out": state.tokens_out,
            "steps": [s.model_dump(mode="json") for s in state.steps],
            "error": state.error,
        },
        "evidence": [e.model_dump(mode="json") for e in state.evidence],
        "recommendations": [RecommendationOut.model_validate(r).model_dump() for r in recs],
    }
