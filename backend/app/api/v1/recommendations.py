# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.events.bus import publish
from app.models import orm
from app.schemas.common import ApprovalDecision, ApprovalHistoryItem, RecommendationOut
from app.security.auth import User, can_approve, current_user
from app.services.action_adapter import execute as execute_action

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=dict)
def list_recommendations(
    status: str | None = None,
    priority: str | None = None,
    exception_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    stmt = select(orm.Recommendation)
    if status:
        stmt = stmt.where(orm.Recommendation.status == status)
    if priority:
        stmt = stmt.where(orm.Recommendation.priority == priority)
    if exception_id:
        stmt = stmt.where(orm.Recommendation.exception_id == exception_id)
    rows = session.execute(stmt.order_by(orm.Recommendation.created_at.desc()).offset(offset).limit(limit)).scalars().all()
    return {"items": [RecommendationOut.model_validate(r).model_dump() for r in rows]}


@router.get("/{recommendation_id}", response_model=dict)
def get_recommendation(
    recommendation_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    row = session.get(orm.Recommendation, recommendation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    history = session.execute(
        select(orm.ApprovalEvent).where(orm.ApprovalEvent.recommendation_id == recommendation_id)
        .order_by(orm.ApprovalEvent.created_at.asc())
    ).scalars().all()
    return {
        "recommendation": RecommendationOut.model_validate(row).model_dump(),
        "history": [ApprovalHistoryItem(
            user=h.user, role=h.role, decision=h.decision, comment=h.comment, created_at=h.created_at
        ).model_dump() for h in history],
    }


def _record(session: Session, rec: orm.Recommendation, user: User, decision: str, comment: str | None) -> None:
    session.add(orm.ApprovalEvent(
        recommendation_id=rec.recommendation_id, user=user.username, role=user.role.value,
        decision=decision, comment=comment,
    ))


@router.post("/{recommendation_id}/approve")
def approve(
    recommendation_id: str,
    body: ApprovalDecision,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    row = session.get(orm.Recommendation, recommendation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if row.status not in ("PENDING_APPROVAL", "EVIDENCE_REQUESTED"):
        raise HTTPException(status_code=409, detail=f"Cannot approve from status {row.status}")
    if not can_approve(user, row.risk_tier):
        raise HTTPException(status_code=403, detail=f"Role {user.role} cannot approve risk tier {row.risk_tier}")
    row.status = "APPROVED"
    _record(session, row, user, "APPROVE", body.comment)
    publish(session, "RecommendationApproved", {"recommendation_id": row.recommendation_id, "approver": user.username})
    # Execute via simulated adapter
    execute_action(session, row.recommendation_id, row.action_type, user.username)
    row.status = "EXECUTED"
    session.commit()
    return {"recommendation_id": recommendation_id, "status": row.status}


@router.post("/{recommendation_id}/reject")
def reject(
    recommendation_id: str,
    body: ApprovalDecision,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    row = session.get(orm.Recommendation, recommendation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if row.status not in ("PENDING_APPROVAL", "EVIDENCE_REQUESTED"):
        raise HTTPException(status_code=409, detail=f"Cannot reject from status {row.status}")
    row.status = "REJECTED"
    _record(session, row, user, "REJECT", body.comment)
    publish(session, "RecommendationRejected", {"recommendation_id": row.recommendation_id, "approver": user.username})
    session.commit()
    return {"recommendation_id": recommendation_id, "status": row.status}


@router.post("/{recommendation_id}/request-evidence")
def request_evidence(
    recommendation_id: str,
    body: ApprovalDecision,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    row = session.get(orm.Recommendation, recommendation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if row.status not in ("PENDING_APPROVAL",):
        raise HTTPException(status_code=409, detail=f"Cannot request evidence from status {row.status}")
    row.status = "EVIDENCE_REQUESTED"
    _record(session, row, user, "REQUEST_EVIDENCE", body.comment)
    session.commit()
    return {"recommendation_id": recommendation_id, "status": row.status}
