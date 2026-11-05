# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.core.config import get_settings
from app.core.db import engine
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = "ok"
    try:
        with engine().connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e!s}"
    s = get_settings()
    return HealthResponse(status="ok", version=__version__, llm_provider=s.llm_provider, db=db_status)
