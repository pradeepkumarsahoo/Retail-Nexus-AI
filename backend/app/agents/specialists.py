# Author: Pradeep Sahoo — Retail Nexus AI
"""Specialist agents. Each produces a Pydantic-validated `EvidenceEntry`.

They are plain Python functions. The LLM is used only to compose rationale and
confidence narration over the deterministic numeric evidence; it does not invent
numbers.

Every agent is wrapped by `ThreatGuard` which enforces the OWASP Top 7 for LLM
applications on the agent's inputs, tool calls, and LLM output before anything
is persisted to the evidence log.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents.llm import LLMProvider
from app.agents.state import AgentState, AgentStep, EvidenceEntry, ToolCall
from app.agents import tools as T
from app.core.logging import get_logger
from app.security.threat_model import ThreatGuard, ThreatViolation, guard_for

log = get_logger("agents")


SYSTEM_BASE = (
    "You are a supply chain analyst. The evidence block below was computed by "
    "deterministic engines; do not alter the numbers. Produce a JSON object "
    "with keys: rationale (<=2 sentences explaining the numbers), confidence (0-1), "
    "signals (echo of the evidence). Reply with JSON only."
)


def _run_llm(
    llm: LLMProvider,
    evidence: dict[str, Any],
    guard: ThreatGuard,
) -> tuple[str, float, int, int]:
    user = json.dumps({"evidence": evidence})
    resp = llm.complete_json(SYSTEM_BASE, user)
    rationale = ""
    conf = 0.5
    try:
        parsed = json.loads(resp.text)
        # LLM05 — Improper Output Handling: validate the JSON shape before use.
        if not isinstance(parsed, dict):
            raise ValueError("llm returned non-object json")
        rationale = str(parsed.get("rationale", ""))[:800]
        raw_conf = parsed.get("confidence", 0.5)
        conf = float(raw_conf)
    except Exception as e:
        guard._emit("LLM05", "warn", "llm output failed schema validation",
                    detail={"error": str(e)[:120]})
    # LLM02/LLM07 — sanitize the rationale before persisting it.
    rationale = guard.sanitize_output(rationale, system=SYSTEM_BASE)
    conf = max(0.0, min(1.0, conf))
    return rationale, conf, resp.tokens_in, resp.tokens_out


def _step(name: str, started: datetime, outputs: dict, tool_calls: list[ToolCall]) -> AgentStep:
    return AgentStep(
        name=name, started_at=started, finished_at=datetime.now(timezone.utc),
        status="success", outputs=outputs, tool_calls=tool_calls,
    )


def _record_security(state: AgentState, guard: ThreatGuard, step: AgentStep) -> None:
    """Attach the guard's findings to both the state audit list and the step."""
    guard.record(state)
    if guard.findings:
        step.outputs.setdefault("security_findings",
                                [f.to_dict() for f in guard.findings])


def demand_agent(session: Session, llm: LLMProvider, state: AgentState) -> AgentState:
    started = datetime.now(timezone.utc)
    tool_calls: list[ToolCall] = []
    guard = guard_for("demand_agent", llm.name, llm.model)
    if not state.product_id or not state.store_id:
        step = _step("demand_agent", started, {"skipped": "no product/store"}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
        return state
    try:
        # LLM03/LLM06 — verify this agent is authorized to call the tool.
        guard.guard_tool_call("forecast_demand",
                              {"product_id": state.product_id,
                               "store_id": state.store_id,
                               "horizon_days": 14})
        fx = T.forecast_demand(session, state.product_id, state.store_id, horizon_days=14)
        tool_calls.append(ToolCall(name="forecast_demand", args={"product_id": state.product_id, "store_id": state.store_id, "horizon_days": 14}, result=fx))
        evidence_payload = {
            "mean_daily": fx.get("mean_daily"),
            "demand_cv": fx.get("demand_cv"),
            "promotion_days_14": fx.get("promotion_days_14"),
            "model": fx.get("model"),
            "exception_evidence": state.exception_evidence,
        }
        # LLM01/02/03/04/06 — preflight sanitization + bound-checks.
        safe_payload = guard.preflight(state, system=SYSTEM_BASE, user_payload=evidence_payload)
        rationale, conf, t_in, t_out = _run_llm(llm, safe_payload, guard)
        state.tokens_in += t_in
        state.tokens_out += t_out
        state.evidence.append(EvidenceEntry(
            source="demand_agent", data={"forecast": fx},
            rationale=rationale, confidence=conf,
        ))
        step = _step("demand_agent", started, {"rationale": rationale, "confidence": conf}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
    except ThreatViolation as tv:
        log.error("threat_block", agent="demand", err=str(tv))
        step = AgentStep(
            name="demand_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=f"blocked by threat guard: {tv}", tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    except Exception as e:
        log.error("agent_error", agent="demand", err=str(e))
        step = AgentStep(
            name="demand_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=str(e), tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    return state


def inventory_agent(session: Session, llm: LLMProvider, state: AgentState) -> AgentState:
    started = datetime.now(timezone.utc)
    tool_calls: list[ToolCall] = []
    guard = guard_for("inventory_agent", llm.name, llm.model)
    if not state.product_id or not state.store_id:
        step = _step("inventory_agent", started, {"skipped": "no product/store"}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
        return state
    try:
        guard.guard_tool_call("stockout_probability",
                              {"product_id": state.product_id,
                               "store_id": state.store_id,
                               "horizon_days": 14})
        p = T.stockout_probability(session, state.product_id, state.store_id, 14)
        tool_calls.append(ToolCall(name="stockout_probability", args={"product_id": state.product_id, "store_id": state.store_id, "horizon_days": 14}, result=p))
        guard.guard_tool_call("find_transfer_candidates",
                              {"product_id": state.product_id,
                               "store_id": state.store_id})
        transfers = T.find_transfer_candidates(session, state.product_id, state.store_id)
        tool_calls.append(ToolCall(name="find_transfer_candidates", args={"product_id": state.product_id, "store_id": state.store_id}, result=transfers))
        evidence_payload = {
            "probability": p["probability"],
            "days_of_supply": next((f["value"] for f in p["contributing_factors"] if f["name"] == "days_of_supply"), None),
            "supplier_otd_avg": p.get("supplier_otd_avg"),
            "transfer_candidate_count": len(transfers.get("candidates", [])),
        }
        safe_payload = guard.preflight(state, system=SYSTEM_BASE, user_payload=evidence_payload)
        rationale, conf, t_in, t_out = _run_llm(llm, safe_payload, guard)
        state.tokens_in += t_in; state.tokens_out += t_out
        state.evidence.append(EvidenceEntry(
            source="inventory_agent",
            data={"stockout": p, "transfers": transfers},
            rationale=rationale, confidence=conf,
        ))
        step = _step("inventory_agent", started, {"rationale": rationale, "confidence": conf}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
    except ThreatViolation as tv:
        log.error("threat_block", agent="inventory", err=str(tv))
        step = AgentStep(
            name="inventory_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=f"blocked by threat guard: {tv}", tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    except Exception as e:
        log.error("agent_error", agent="inventory", err=str(e))
        step = AgentStep(
            name="inventory_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=str(e), tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    return state


def supplier_agent(session: Session, llm: LLMProvider, state: AgentState) -> AgentState:
    started = datetime.now(timezone.utc)
    tool_calls: list[ToolCall] = []
    guard = guard_for("supplier_agent", llm.name, llm.model)
    sup_id = state.supplier_id
    if not sup_id and state.product_id:
        guard.guard_tool_call("find_alt_suppliers", {"product_id": state.product_id})
        alt = T.find_alt_suppliers(session, state.product_id)
        tool_calls.append(ToolCall(name="find_alt_suppliers", args={"product_id": state.product_id}, result=alt))
        candidates = alt.get("alternatives", [])
        if candidates:
            sup_id = candidates[0]["supplier_id"]
    if not sup_id:
        step = _step("supplier_agent", started, {"skipped": "no supplier context"}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
        return state
    try:
        guard.guard_tool_call("supplier_reliability", {"supplier_id": sup_id})
        r = T.supplier_reliability(session, sup_id)
        tool_calls.append(ToolCall(name="supplier_reliability", args={"supplier_id": sup_id}, result=r))
        evidence_payload = {
            "stats": r["stats"], "risk_score": r["risk_score"], "risk_category": r["risk_category"],
        }
        safe_payload = guard.preflight(state, system=SYSTEM_BASE, user_payload=evidence_payload)
        rationale, conf, t_in, t_out = _run_llm(llm, safe_payload, guard)
        state.tokens_in += t_in; state.tokens_out += t_out
        state.evidence.append(EvidenceEntry(
            source="supplier_agent", data={"risk": r},
            rationale=rationale, confidence=conf,
        ))
        step = _step("supplier_agent", started, {"rationale": rationale, "confidence": conf}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
    except ThreatViolation as tv:
        log.error("threat_block", agent="supplier", err=str(tv))
        step = AgentStep(
            name="supplier_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=f"blocked by threat guard: {tv}", tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    except Exception as e:
        log.error("agent_error", agent="supplier", err=str(e))
        step = AgentStep(
            name="supplier_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=str(e), tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    return state


def alt_sourcing_agent(session: Session, llm: LLMProvider, state: AgentState) -> AgentState:
    started = datetime.now(timezone.utc)
    tool_calls: list[ToolCall] = []
    guard = guard_for("alt_sourcing_agent", llm.name, llm.model)
    if not state.product_id:
        step = _step("alt_sourcing_agent", started, {"skipped": "no product"}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
        return state
    try:
        guard.guard_tool_call("find_alt_suppliers", {"product_id": state.product_id})
        alts = T.find_alt_suppliers(session, state.product_id)
        tool_calls.append(ToolCall(name="find_alt_suppliers", args={"product_id": state.product_id}, result=alts))
        evidence_payload = {
            "alternative_count": len(alts.get("alternatives", [])),
            "best_alt_otd": alts["alternatives"][0]["on_time_delivery_pct"] if alts.get("alternatives") else None,
        }
        safe_payload = guard.preflight(state, system=SYSTEM_BASE, user_payload=evidence_payload)
        rationale, conf, t_in, t_out = _run_llm(llm, safe_payload, guard)
        state.tokens_in += t_in; state.tokens_out += t_out
        state.evidence.append(EvidenceEntry(
            source="alt_sourcing_agent", data={"alternatives": alts},
            rationale=rationale, confidence=conf,
        ))
        step = _step("alt_sourcing_agent", started, {"rationale": rationale, "confidence": conf}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
    except ThreatViolation as tv:
        log.error("threat_block", agent="alt_sourcing", err=str(tv))
        step = AgentStep(
            name="alt_sourcing_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=f"blocked by threat guard: {tv}", tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    except Exception as e:
        log.error("agent_error", agent="alt_sourcing", err=str(e))
        step = AgentStep(
            name="alt_sourcing_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=str(e), tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    return state


def business_impact_agent(session: Session, llm: LLMProvider, state: AgentState) -> AgentState:
    """Combines the evidence into a revenue-at-risk estimate."""
    started = datetime.now(timezone.utc)
    tool_calls: list[ToolCall] = []
    guard = guard_for("business_impact_agent", llm.name, llm.model)
    try:
        if state.product_id:
            guard.guard_tool_call("lookup_product", {"product_id": state.product_id})
        product = T.lookup_product(session, state.product_id) if state.product_id else {}
        tool_calls.append(ToolCall(name="lookup_product", args={"product_id": state.product_id}, result=product))
        unit_price = float(product.get("unit_price", 0.0))
        unit_cost = float(product.get("unit_cost", 0.0))
        inv_entry = next((e for e in state.evidence if e.source == "inventory_agent"), None)
        prob = 0.0
        horizon = 14
        mean_daily = 0.0
        if inv_entry:
            p = inv_entry.data.get("stockout", {})
            prob = float(p.get("probability", 0.0))
            horizon = int(p.get("horizon_days", 14))
            mean_daily = float(p.get("data", {}).get("mean_daily_demand", 0.0))
        revenue_at_risk = round(prob * mean_daily * horizon * unit_price, 2)
        expedite_cost = round(unit_cost * 0.15 * mean_daily * horizon, 2)
        transfer_cost = round(unit_cost * 0.08 * mean_daily * horizon, 2)
        net_expedite = round(revenue_at_risk - expedite_cost, 2)
        net_transfer = round(revenue_at_risk - transfer_cost, 2)
        payload = {
            "unit_price": unit_price, "unit_cost": unit_cost,
            "stockout_probability": prob, "mean_daily_demand": mean_daily,
            "revenue_at_risk": revenue_at_risk,
            "expected_expedite_cost": expedite_cost,
            "expected_transfer_cost": transfer_cost,
            "net_benefit_expedite": net_expedite,
            "net_benefit_transfer": net_transfer,
        }
        safe_payload = guard.preflight(state, system=SYSTEM_BASE, user_payload=payload)
        rationale, conf, t_in, t_out = _run_llm(llm, safe_payload, guard)
        state.tokens_in += t_in; state.tokens_out += t_out
        state.evidence.append(EvidenceEntry(
            source="business_impact_agent", data=payload,
            rationale=rationale, confidence=conf,
        ))
        step = _step("business_impact_agent", started, {"rationale": rationale, "confidence": conf}, tool_calls)
        _record_security(state, guard, step)
        state.steps.append(step)
    except ThreatViolation as tv:
        log.error("threat_block", agent="business_impact", err=str(tv))
        step = AgentStep(
            name="business_impact_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=f"blocked by threat guard: {tv}", tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    except Exception as e:
        log.error("agent_error", agent="business_impact", err=str(e))
        step = AgentStep(
            name="business_impact_agent", started_at=started, finished_at=datetime.now(timezone.utc),
            status="error", error=str(e), tool_calls=tool_calls,
        )
        _record_security(state, guard, step)
        state.steps.append(step)
    return state
