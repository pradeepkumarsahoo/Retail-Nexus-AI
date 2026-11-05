# Author: Pradeep Sahoo — Retail Nexus AI
"""Typed state passed between agents (LangGraph-equivalent)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceEntry(BaseModel):
    source: str
    produced_at: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    confidence: float = 0.0


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None


class AgentStep(BaseModel):
    name: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    error: str | None = None


class AgentState(BaseModel):
    exception_id: str
    category: str
    product_id: str | None
    store_id: str | None
    supplier_id: str | None
    exception_evidence: dict[str, Any] = Field(default_factory=dict)
    agents_to_run: list[str] = Field(default_factory=list)
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    provider: str = "mock"
    model: str = "mock-small"
    error: str | None = None
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    requires_approval: bool = True
    risk_tier: str = "MEDIUM"
    security_findings: list[dict[str, Any]] = Field(default_factory=list)


class RecommendationDraft(BaseModel):
    recommendation_id: str
    exception_id: str
    action_type: str
    priority: str
    affected_products: list[str] = Field(default_factory=list)
    affected_stores: list[str] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    business_rationale: str
    estimated_revenue_at_risk: float
    estimated_intervention_cost: float
    estimated_net_benefit: float
    confidence: float
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    requires_approval: bool = True
    risk_tier: str = "MEDIUM"
