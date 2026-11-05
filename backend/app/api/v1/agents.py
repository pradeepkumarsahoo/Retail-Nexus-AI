# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.models import orm
from app.schemas.common import AgentRunOut
from app.security.auth import User, current_user

router = APIRouter()


@router.get("/agents/runs")
def list_runs(
    exception_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> dict:
    stmt = select(orm.AgentRun).order_by(orm.AgentRun.started_at.desc()).limit(limit)
    if exception_id:
        stmt = stmt.where(orm.AgentRun.exception_id == exception_id)
    rows = session.execute(stmt).scalars().all()
    return {"items": [AgentRunOut.model_validate(r).model_dump(mode="json") for r in rows]}
