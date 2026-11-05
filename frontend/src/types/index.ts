// Author: Pradeep Sahoo — Retail Nexus AI
export interface DashboardSummary {
  active_exceptions: number;
  high_or_critical: number;
  products_at_stockout_risk: number;
  suppliers_at_risk: number;
  estimated_revenue_exposure_usd: number;
  pending_approvals: number;
  exceptions_by_category: Record<string, number>;
  exceptions_by_severity: Record<string, number>;
  trend_last_14_days: Array<{ date: string; total: number; CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number }>;
}

export interface Exception_ {
  exception_id: string;
  category: string;
  product_id: string | null;
  store_id: string | null;
  supplier_id: string | null;
  detected_at: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_score: number;
  evidence: Record<string, any>;
  estimated_impact_usd: number;
  status: string;
  workflow_hint: string | null;
}

export interface Recommendation {
  recommendation_id: string;
  exception_id: string;
  action_type: string;
  priority: string;
  affected_products: string[];
  affected_stores: string[];
  supporting_evidence: Array<Record<string, any>>;
  business_rationale: string;
  estimated_revenue_at_risk: number;
  estimated_intervention_cost: number;
  estimated_net_benefit: number;
  confidence: number;
  assumptions: string[];
  constraints: string[];
  requires_approval: boolean;
  risk_tier: string;
  status: string;
  created_at: string;
}

export interface Supplier {
  supplier_id: string;
  name: string;
  on_time_delivery_pct: number;
  avg_lead_time_days: number;
  lead_time_variance: number;
  late_po_count: number;
  total_po_count: number;
  capacity_units_per_day: number;
}

export interface Product {
  product_id: string;
  name: string;
  category: string;
  unit_cost: number;
  unit_price: number;
  shelf_life_days: number | null;
}

export interface Store {
  store_id: string;
  name: string;
  region: string;
  city: string;
  size_sqft: number;
}

export interface ForecastResponse {
  product_id: string;
  store_id: string;
  model: string;
  horizon_days: number;
  forecast: Array<{ date: string; forecast_units: number }>;
  recent_sales: Array<{ date: string; units: number; promotion: boolean }>;
}

export interface StockoutRisk {
  product_id: string;
  store_id: string;
  horizon_days: number;
  probability: number;
  predicted_stockout_date: string | null;
  risk_category: string;
  contributing_factors: Array<{ source: string; metric: string; value: any; notes?: string | null }>;
  suggested_action: string;
  data: Record<string, any>;
}

export interface AgentRun {
  run_id: string;
  exception_id: string;
  started_at: string;
  finished_at: string | null;
  provider: string;
  model: string;
  status: string;
  steps: Array<any>;
  tokens_in: number;
  tokens_out: number;
  cost_estimate_usd: number;
  error: string | null;
}

export interface SimulationOutcome {
  scenario: string;
  projected_inventory_units: number;
  expected_stockout_units: number;
  expected_lost_sales_units: number;
  revenue_exposure_usd: number;
  intervention_cost_usd: number;
  net_benefit_usd: number;
  assumptions: string[];
  constraints: string[];
}

export interface SimulationResponse {
  exception_id: string;
  horizon_days: number;
  outcomes: SimulationOutcome[];
  recommended_scenario: string;
}
