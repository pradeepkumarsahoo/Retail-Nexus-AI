# Author: Pradeep Sahoo — Retail Nexus AI
"""Simulated action adapter.

Agents and approvals never write to real ERP/WMS/OMS. This module records
intended actions as audit entries and emits an `ActionExecuted` event so the
rest of the system observes the outcome identically to a real adapter.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.events.bus import publish


def execute(session: Session, recommendation_id: str, action_type: str, approver: str) -> dict:
    payload = {
        "recommendation_id": recommendation_id,
        "action_type": action_type,
        "approver": approver,
        "mode": "SIMULATED",
    }
    publish(session, "ActionExecuted", payload)
    return payload
