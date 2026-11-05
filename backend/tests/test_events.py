# Author: Pradeep Sahoo — Retail Nexus AI
"""Event bus — publish into outbox, dispatch once, idempotent on replay."""
from __future__ import annotations


def test_publish_and_dispatch(session):
    from app.events.bus import BROKER, dispatch_pending, publish

    received = []
    BROKER.subscribe("TestEvent", lambda e: received.append(e))
    eid = publish(session, "TestEvent", {"hello": "world"})
    session.commit()
    n = dispatch_pending()
    assert n >= 1
    assert any(r["event_id"] == eid for r in received)
    # Idempotent replay — dispatching again does nothing
    n2 = dispatch_pending()
    assert n2 == 0
