# Author: Pradeep Sahoo — Retail Nexus AI
"""LangGraph-equivalent supervisor.

Nodes:
   entry -> supervisor_router -> {demand, inventory, supplier, alt_sourcing} ->
   business_impact -> aggregate_and_rank -> human_approval_interrupt

Features: conditional edges, per-node timeout (soft), max-step limit, retry with
backoff, checkpointing of state after each node.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session
from tenacity import Retrying, stop_after_attempt, wait_fixed, RetryError

from app.agents.llm import LLMProvider, get_provider
from app.agents.specialists import (
    alt_sourcing_agent,
    business_impact_agent,
    demand_agent,
    inventory_agent,
    supplier_agent,
)
from app.agents.state import AgentState, AgentStep, RecommendationDraft
from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.enums import ActionType, RiskTier
from app.models import orm

log = get_logger("orchestrator")


def _route(category: str) -> list[str]:
    """Decide which agents to invoke based on exception category."""
    c = category.upper()
    if c in ("DEMAND_SPIKE", "DEMAND_DECLINE", "SALES_ANOMALY"):
        return ["demand_agent", "inventory_agent", "business_impact_agent"]
    if c in ("STOCKOUT_RISK", "LOW_DAYS_OF_SUPPLY"):
        return ["demand_agent", "inventory_agent", "supplier_agent", "alt_sourcing_agent", "business_impact_agent"]
    if c in ("SUPPLIER_DELAY", "SUPPLIER_CAPACITY"):
        return ["supplier_agent", "alt_sourcing_agent", "business_impact_agent"]
    if c in ("EXCESS_INVENTORY", "AGING_INVENTORY"):
        return ["demand_agent", "inventory_agent", "business_impact_agent"]
    if c == "REGIONAL_DISRUPTION":
        return ["supplier_agent", "alt_sourcing_agent", "business_impact_agent"]
    if c == "REPLENISHMENT_MISMATCH":
        return ["demand_agent", "inventory_agent", "business_impact_agent"]
    return ["demand_agent", "inventory_agent", "business_impact_agent"]


_NODE_IMPL: dict[str, Callable[[Session, LLMProvider, AgentState], AgentState]] = {
    "demand_agent": demand_agent,
    "inventory_agent": inventory_agent,
    "supplier_agent": supplier_agent,
    "alt_sourcing_agent": alt_sourcing_agent,
    "business_impact_agent": business_impact_agent,
}


def _run_node(name: str, session: Session, llm: LLMProvider, state: AgentState, timeout_s: int) -> AgentState:
    impl = _NODE_IMPL[name]
    t0 = time.perf_counter()

    def _call() -> AgentState:
        return impl(session, llm, state)

    try:
        for attempt in Retrying(stop=stop_after_attempt(get_settings().agent_max_retries + 1),
                                wait=wait_fixed(0.4), reraise=True):
            with attempt:
                s = _call()
                dur = time.perf_counter() - t0
                if dur > timeout_s:
                    # Soft timeout: log and keep going. Hard-killing a Python call inside a request
                    # is not safe without a worker — document that.
                    log.warning("node_slow", node=name, duration_s=round(dur, 2))
                return s
    except RetryError as e:
        state.steps.append(AgentStep(
            name=name, started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="error", error=f"retry_exhausted: {e!s}",
        ))
        return state
    return state


def _rank_recommendations(drafts: list[RecommendationDraft]) -> list[RecommendationDraft]:
    def key(d: RecommendationDraft):
        tier = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFORMATIONAL": 0}.get(d.risk_tier, 2)
        return (-tier, -d.estimated_net_benefit, -d.confidence)
    return sorted(drafts, key=key)


def _risk_tier_from(prob: float, net_benefit: float) -> str:
    if prob >= 0.75 or net_benefit >= 5000:
        return RiskTier.CRITICAL.value
    if prob >= 0.5 or net_benefit >= 1500:
        return RiskTier.HIGH.value
    if prob >= 0.3:
        return RiskTier.MEDIUM.value
    if prob >= 0.1:
        return RiskTier.LOW.value
    return RiskTier.INFORMATIONAL.value


def _draft_recommendations(state: AgentState) -> list[RecommendationDraft]:
    inv_entry = next((e for e in state.evidence if e.source == "inventory_agent"), None)
    biz_entry = next((e for e in state.evidence if e.source == "business_impact_agent"), None)
    alt_entry = next((e for e in state.evidence if e.source == "alt_sourcing_agent"), None)
    supp_entry = next((e for e in state.evidence if e.source == "supplier_agent"), None)
    drafts: list[RecommendationDraft] = []

    supporting = [
        {"source": e.source, "rationale": e.rationale, "confidence": e.confidence}
        for e in state.evidence
    ]

    prob = 0.0
    transfer_candidates: list[dict] = []
    if inv_entry:
        prob = float(inv_entry.data.get("stockout", {}).get("probability", 0.0))
        transfer_candidates = inv_entry.data.get("transfers", {}).get("candidates", []) or []

    revenue_at_risk = float(biz_entry.data.get("revenue_at_risk", 0.0)) if biz_entry else 0.0

    if state.category in ("STOCKOUT_RISK", "LOW_DAYS_OF_SUPPLY") and prob >= 0.3:
        # Transfer recommendation (if a candidate exists)
        if transfer_candidates:
            donor = transfer_candidates[0]
            move_units = min(int(donor.get("available_units", 0)) // 2, 200)
            expected_transfer_cost = float(biz_entry.data.get("expected_transfer_cost", 0.0)) if biz_entry else 0.0
            net_benefit = round(revenue_at_risk - expected_transfer_cost, 2)
            drafts.append(RecommendationDraft(
                recommendation_id=f"REC-{uuid.uuid4().hex[:10].upper()}",
                exception_id=state.exception_id,
                action_type=ActionType.TRANSFER_INVENTORY.value,
                priority="HIGH" if prob >= 0.5 else "MEDIUM",
                affected_products=[state.product_id] if state.product_id else [],
                affected_stores=[state.store_id, donor["from_store_id"]] if state.store_id else [donor["from_store_id"]],
                supporting_evidence=supporting,
                business_rationale=(
                    f"Transfer {move_units} units from store {donor.get('from_store_name', donor['from_store_id'])} "
                    f"(donor DoS={donor.get('donor_days_of_supply')}) to protect the at-risk store "
                    f"(stockout probability={prob:.2f})."
                ),
                estimated_revenue_at_risk=revenue_at_risk,
                estimated_intervention_cost=expected_transfer_cost,
                estimated_net_benefit=net_benefit,
                confidence=min(1.0, prob),
                assumptions=[
                    "Transfer arrives in 1 business day.",
                    "Donor store continues to meet its own demand after the transfer.",
                    "Unit price and cost taken from the product master.",
                ],
                constraints=[],
                requires_approval=True,
                risk_tier=_risk_tier_from(prob, net_benefit),
            ))
        # Expedite recommendation if we have an open PO (deducible from inventory agent payload)
        expedite_cost = float(biz_entry.data.get("expected_expedite_cost", 0.0)) if biz_entry else 0.0
        if expedite_cost > 0:
            net = round(revenue_at_risk - expedite_cost, 2)
            drafts.append(RecommendationDraft(
                recommendation_id=f"REC-{uuid.uuid4().hex[:10].upper()}",
                exception_id=state.exception_id,
                action_type=ActionType.EXPEDITE_PO.value,
                priority="HIGH" if prob >= 0.5 else "MEDIUM",
                affected_products=[state.product_id] if state.product_id else [],
                affected_stores=[state.store_id] if state.store_id else [],
                supporting_evidence=supporting,
                business_rationale=(
                    f"Expedite the open replenishment to compress supplier lead time. "
                    f"Revenue at risk ≈ ${revenue_at_risk:.2f}; expedite ≈ ${expedite_cost:.2f}."
                ),
                estimated_revenue_at_risk=revenue_at_risk,
                estimated_intervention_cost=expedite_cost,
                estimated_net_benefit=net,
                confidence=min(1.0, prob),
                assumptions=["Expedite accelerates arrival by ~5 days at +15% unit cost."],
                constraints=[],
                requires_approval=True,
                risk_tier=_risk_tier_from(prob, net),
            ))
    elif state.category in ("SUPPLIER_DELAY", "SUPPLIER_CAPACITY") and supp_entry:
        alts = alt_entry.data.get("alternatives", {}).get("alternatives", []) if alt_entry else []
        if alts:
            best = alts[0]
            drafts.append(RecommendationDraft(
                recommendation_id=f"REC-{uuid.uuid4().hex[:10].upper()}",
                exception_id=state.exception_id,
                action_type=ActionType.SWITCH_SUPPLIER.value,
                priority="HIGH",
                affected_products=[state.product_id] if state.product_id else [],
                affected_stores=[],
                supporting_evidence=supporting,
                business_rationale=(
                    f"Current supplier reliability flagged. Alt supplier {best['name']} offers "
                    f"OTD {best['on_time_delivery_pct']:.2%} with {best['lead_time_days']}-day lead time."
                ),
                estimated_revenue_at_risk=revenue_at_risk,
                estimated_intervention_cost=0.0,
                estimated_net_benefit=revenue_at_risk,
                confidence=0.6,
                assumptions=["Alt supplier capacity meets the required volume.",
                             "Any ramp-up cost of switching is excluded from this estimate."],
                constraints=["Switch requires procurement approval."],
                requires_approval=True,
                risk_tier=RiskTier.HIGH.value,
            ))
    elif state.category in ("EXCESS_INVENTORY", "AGING_INVENTORY"):
        drafts.append(RecommendationDraft(
            recommendation_id=f"REC-{uuid.uuid4().hex[:10].upper()}",
            exception_id=state.exception_id,
            action_type=ActionType.REDUCE_REPLENISHMENT.value,
            priority="MEDIUM",
            affected_products=[state.product_id] if state.product_id else [],
            affected_stores=[state.store_id] if state.store_id else [],
            supporting_evidence=supporting,
            business_rationale="Reduce next replenishment cycle to work down excess inventory and avoid shelf-life loss.",
            estimated_revenue_at_risk=0.0,
            estimated_intervention_cost=0.0,
            estimated_net_benefit=max(0.0, revenue_at_risk),  # avoided waste
            confidence=0.6,
            assumptions=["Downstream demand is stable."],
            constraints=[],
            requires_approval=True,
            risk_tier=RiskTier.LOW.value,
        ))
    else:
        # Fallback: a MONITOR recommendation that always meets the schema
        drafts.append(RecommendationDraft(
            recommendation_id=f"REC-{uuid.uuid4().hex[:10].upper()}",
            exception_id=state.exception_id,
            action_type=ActionType.MONITOR.value,
            priority="LOW",
            affected_products=[state.product_id] if state.product_id else [],
            affected_stores=[state.store_id] if state.store_id else [],
            supporting_evidence=supporting,
            business_rationale="Signal recorded; continue monitoring. No consequential action proposed.",
            estimated_revenue_at_risk=revenue_at_risk,
            estimated_intervention_cost=0.0,
            estimated_net_benefit=0.0,
            confidence=0.3,
            assumptions=["No intervention needed at this time."],
            constraints=[],
            requires_approval=False,
            risk_tier=RiskTier.INFORMATIONAL.value,
        ))

    return _rank_recommendations(drafts)


def investigate(
    session: Session,
    exception_row: orm.Exception_,
    llm: LLMProvider | None = None,
    checkpoint: Callable[[AgentState], None] | None = None,
) -> AgentState:
    """Run the full workflow for a single exception; persist AgentRun + draft recommendations."""
    settings = get_settings()
    llm = llm or get_provider()
    state = AgentState(
        exception_id=exception_row.exception_id,
        category=exception_row.category,
        product_id=exception_row.product_id,
        store_id=exception_row.store_id,
        supplier_id=exception_row.supplier_id,
        exception_evidence=exception_row.evidence or {},
        agents_to_run=_route(exception_row.category),
        provider=llm.name,
        model=llm.model,
    )
    run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
    run = orm.AgentRun(
        run_id=run_id, exception_id=state.exception_id,
        provider=llm.name, model=llm.model, status="RUNNING",
        steps=[],
    )
    session.add(run)
    session.flush()

    step_count = 0
    for node in state.agents_to_run:
        if step_count >= settings.agent_max_steps:
            state.error = f"max_steps_exceeded ({settings.agent_max_steps})"
            break
        state = _run_node(node, session, llm, state, settings.agent_step_timeout_seconds)
        step_count += 1
        if checkpoint:
            checkpoint(state)
    # Draft recommendations
    drafts = _draft_recommendations(state)
    state.recommendations = [d.model_dump() for d in drafts]
    # Persist recommendations
    for d in drafts:
        session.add(orm.Recommendation(**d.model_dump()))

    # Persist run summary
    run.status = "FAILED" if state.error else "SUCCEEDED"
    run.finished_at = datetime.now(timezone.utc)
    run.steps = [s.model_dump(mode="json") for s in state.steps]
    run.tokens_in = state.tokens_in
    run.tokens_out = state.tokens_out
    run.cost_estimate_usd = 0.0  # mock
    run.error = state.error

    # Update exception status
    exception_row.status = "RECOMMENDATION_READY" if drafts else "INVESTIGATING"
    session.flush()
    return state
