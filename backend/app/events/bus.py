# Author: Pradeep Sahoo — Retail Nexus AI
"""Outbox-pattern event dispatcher.

Writes events to the `outbox_events` table in the same transaction as the business state
change (callers do this). A dispatcher sweeps PENDING rows and hands them to in-process
subscribers. Mapping to SQS/SNS/EventBridge is a trivial adapter swap — see
`docs/decisions/0004-events.md`.
"""
from __future__ import annotations

import json
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import session_scope
from app.core.logging import get_logger
from app.models import orm

log = get_logger("events")

Handler = Callable[[dict], None]


class InProcessBroker:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.Lock()
        self._processed_ids: set[str] = set()

    def subscribe(self, event_type: str, handler: Handler) -> None:
        with self._lock:
            self._handlers[event_type].append(handler)

    def dispatch(self, event: dict) -> None:
        if event["event_id"] in self._processed_ids:
            return  # idempotent
        for h in self._handlers.get(event["event_type"], []):
            try:
                h(event)
            except Exception as e:
                log.error("handler_error", event=event["event_type"], err=str(e))
        self._processed_ids.add(event["event_id"])


BROKER = InProcessBroker()


def publish(session: Session, event_type: str, payload: dict, *, correlation_id: str | None = None,
            source: str = "control-tower") -> str:
    """Insert into outbox within the current session's transaction."""
    eid = f"EVT-{uuid.uuid4().hex}"
    row = orm.OutboxEvent(
        event_id=eid, event_type=event_type, correlation_id=correlation_id,
        source=source, schema_version="1", payload=payload, status="PENDING",
    )
    session.add(row)
    return eid


def dispatch_pending(limit: int = 100) -> int:
    """Dispatch PENDING outbox events to the in-process broker. Returns count dispatched."""
    count = 0
    with session_scope() as s:
        rows = s.execute(
            select(orm.OutboxEvent).where(orm.OutboxEvent.status == "PENDING").limit(limit)
        ).scalars().all()
        for r in rows:
            evt = {
                "event_id": r.event_id,
                "event_type": r.event_type,
                "correlation_id": r.correlation_id,
                "source": r.source,
                "schema_version": r.schema_version,
                "payload": r.payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            BROKER.dispatch(evt)
            r.status = "DISPATCHED"
            r.dispatched_at = datetime.now(timezone.utc)
            count += 1
    return count


# Example subscribers — kept lightweight; the real subscribers live in services.
def _log_handler(evt: dict) -> None:
    log.info("event_dispatched", type=evt["event_type"], id=evt["event_id"])


BROKER.subscribe("StockoutRiskDetected", _log_handler)
BROKER.subscribe("DemandAnomalyDetected", _log_handler)
BROKER.subscribe("SupplierRiskDetected", _log_handler)
BROKER.subscribe("RecommendationGenerated", _log_handler)
BROKER.subscribe("RecommendationApproved", _log_handler)
BROKER.subscribe("RecommendationRejected", _log_handler)
BROKER.subscribe("ActionExecuted", _log_handler)
