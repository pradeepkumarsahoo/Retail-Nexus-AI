# Author: Pradeep Sahoo — Retail Nexus AI
"""Shared Pydantic schemas for API I/O."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from app.domain.enums import (
    ActionType,
    ExceptionCategory,
    ExceptionStatus,
    RecommendationStatus,
    RiskTier,
    Severity,
)


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductOut(ORMBase):
    product_id: str
    name: str
    category: str
    unit_cost: float
    unit_price: float
    shelf_life_days: int | None = None


class StoreOut(ORMBase):
    store_id: str
    name: str
    region: str
    city: str
    size_sqft: int


class SupplierOut(ORMBase):
    supplier_id: str
    name: str
    region: str
    nominal_lead_time_days: int
    capacity_units_per_day: int
    min_order_qty: int
    reliability_hint: float


class SupplierPerformance(BaseModel):
    supplier_id: str
    name: str
    on_time_delivery_pct: float
    avg_lead_time_days: float
    lead_time_variance: float
    late_po_count: int
    total_po_count: int
    capacity_units_per_day: int


class EvidenceItem(BaseModel):
    source: str = Field(..., description="Which agent/engine produced this evidence")
    metric: str
    value: Any
    unit: str | None = None
    notes: str | None = None


class ExceptionOut(ORMBase):
    exception_id: str
    category: ExceptionCategory
    product_id: str | None
    store_id: str | None
    supplier_id: str | None
    detected_at: datetime
    severity: Severity
    risk_score: float
    evidence: dict[str, Any]
    estimated_impact_usd: float
    status: ExceptionStatus
    workflow_hint: str | None = None


class RecommendationOut(ORMBase):
    recommendation_id: str
    exception_id: str
    action_type: ActionType
    priority: str
    affected_products: list[str]
    affected_stores: list[str]
    supporting_evidence: list[dict[str, Any]]
    business_rationale: str
    estimated_revenue_at_risk: float
    estimated_intervention_cost: float
    estimated_net_benefit: float
    confidence: float
    assumptions: list[str]
    constraints: list[str]
    requires_approval: bool
    risk_tier: RiskTier
    status: RecommendationStatus
    created_at: datetime


class ApprovalDecision(BaseModel):
    comment: str | None = None


class ApprovalHistoryItem(BaseModel):
    user: str
    role: str
    decision: str
    comment: str | None
    created_at: datetime


class SimulationScenario(BaseModel):
    name: str = Field(..., description="BASELINE | EXPEDITE | TRANSFER | SWITCH_SUPPLIER | INCREASE_REPLENISHMENT")
    params: dict[str, Any] = Field(default_factory=dict)


class SimulationRequest(BaseModel):
    exception_id: str
    scenarios: list[SimulationScenario]
    horizon_days: int = 14


class ScenarioOutcome(BaseModel):
    scenario: str
    projected_inventory_units: int
    expected_stockout_units: int
    expected_lost_sales_units: int
    revenue_exposure_usd: float
    intervention_cost_usd: float
    net_benefit_usd: float
    assumptions: list[str]
    constraints: list[str]


class SimulationResponse(BaseModel):
    exception_id: str
    horizon_days: int
    outcomes: list[ScenarioOutcome]
    recommended_scenario: str


class ForecastPoint(BaseModel):
    date: date
    forecast_units: float
    lower_bound: float | None = None
    upper_bound: float | None = None


class ForecastResponse(BaseModel):
    product_id: str
    store_id: str
    model: str
    horizon_days: int
    forecast: list[ForecastPoint]
    recent_sales: list[dict[str, Any]]


class StockoutRiskResponse(BaseModel):
    product_id: str
    store_id: str
    horizon_days: int
    probability: float
    predicted_stockout_date: date | None
    risk_category: str
    contributing_factors: list[EvidenceItem]
    suggested_action: ActionType
    data: dict[str, Any]


class AgentStep(BaseModel):
    name: str
    started_at: datetime
    finished_at: datetime
    status: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class AgentRunOut(ORMBase):
    run_id: str
    exception_id: str
    started_at: datetime
    finished_at: datetime | None
    provider: str
    model: str
    status: str
    steps: list[dict[str, Any]]
    tokens_in: int
    tokens_out: int
    cost_estimate_usd: float
    error: str | None


class DashboardSummary(BaseModel):
    active_exceptions: int
    high_or_critical: int
    products_at_stockout_risk: int
    suppliers_at_risk: int
    estimated_revenue_exposure_usd: float
    pending_approvals: int
    exceptions_by_category: dict[str, int]
    exceptions_by_severity: dict[str, int]
    trend_last_14_days: list[dict[str, Any]]


class IngestResult(BaseModel):
    dataset: str
    rows_accepted: int
    rows_rejected: int
    issues: list[dict[str, Any]]
    source_hash: str | None = None


class Page(BaseModel):
    total: int
    offset: int
    limit: int


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    db: str
