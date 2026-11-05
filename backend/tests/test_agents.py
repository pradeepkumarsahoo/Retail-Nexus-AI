# Author: Pradeep Sahoo — Retail Nexus AI
"""Agent evaluation: routing, evidence completeness, recommendation schema, safe failure."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.orchestration.supervisor import _draft_recommendations, _route


@pytest.fixture(scope="module")
def seeded_small():
    """Load a minimal synthetic set for module-scoped tests."""
    from app.core.db import init_db
    from app.data.generate import GenParams, _rand, gen_products, gen_stores, gen_suppliers, gen_sales_and_inventory_and_events
    from app.data.load import load_all
    init_db()
    tmp = Path(tempfile.mkdtemp(prefix="ct-agents-"))
    p = GenParams(seed=11, days=60, n_products=5, n_stores=2, n_suppliers=3)
    r, npr = _rand(p.seed)
    products = gen_products(p, r)
    stores = gen_stores(p, r)
    suppliers, sup_products = gen_suppliers(p, r, products)
    frames = gen_sales_and_inventory_and_events(p, r, npr, products, stores, suppliers, sup_products)
    import csv
    def _w(name, rows):
        if not rows: return
        with (tmp / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); [w.writerow(r) for r in rows]
    _w("products", products); _w("stores", stores); _w("suppliers", suppliers)
    _w("supplier_products", sup_products)
    _w("sales", frames["sales"]); _w("inventory", frames["inventory"])
    _w("purchase_orders", frames["pos"]); _w("store_transfers", frames["transfers"])
    _w("promotions", frames["promos"])
    load_all(tmp, wipe=True)
    return tmp


def test_routing_by_category():
    # Stockout risk invokes the full chain
    r = _route("STOCKOUT_RISK")
    assert "demand_agent" in r
    assert "supplier_agent" in r
    assert "alt_sourcing_agent" in r
    assert "business_impact_agent" in r
    # Supplier delay skips demand agent
    r2 = _route("SUPPLIER_DELAY")
    assert "supplier_agent" in r2
    assert "demand_agent" not in r2


def test_investigation_produces_valid_recommendation(seeded_small):
    from sqlalchemy import select
    from app.core.db import session_scope
    from app.models import orm
    from app.orchestration.supervisor import investigate
    from app.services.exceptions_engine import detect_all

    with session_scope() as s:
        created = detect_all(s)
        if not created:
            pytest.skip("No exceptions produced under this seed")
        exc = created[0]
        state = investigate(s, exc)
        # Evidence must contain at least one entry per invoked agent
        sources = {e.source for e in state.evidence}
        assert "business_impact_agent" in sources
        # Every recommendation adheres to the required shape
        for r in state.recommendations:
            for key in ("recommendation_id", "exception_id", "action_type", "priority",
                        "affected_products", "affected_stores", "supporting_evidence",
                        "business_rationale", "estimated_revenue_at_risk",
                        "estimated_intervention_cost", "estimated_net_benefit",
                        "confidence", "assumptions", "constraints", "requires_approval", "risk_tier"):
                assert key in r
            assert 0.0 <= r["confidence"] <= 1.0


def test_agent_fallback_when_no_product_store():
    """If the exception lacks product/store, specialists must not crash — they must return 'skipped'."""
    from app.agents.specialists import demand_agent, inventory_agent
    from app.agents.state import AgentState
    from app.agents.llm import MockLLM
    from app.core.db import session_scope

    state = AgentState(
        exception_id="EXC-X", category="SALES_ANOMALY",
        product_id=None, store_id=None, supplier_id=None,
        agents_to_run=["demand_agent"],
    )
    with session_scope() as s:
        state = demand_agent(s, MockLLM(), state)
        state = inventory_agent(s, MockLLM(), state)
    assert state.steps[0].outputs.get("skipped") is not None
    assert state.error is None
