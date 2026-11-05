# Author: Pradeep Sahoo — Retail Nexus AI
"""SQLAlchemy ORM models for Retail Nexus AI."""
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class Product(Base):
    __tablename__ = "products"
    product_id = Column(String(32), primary_key=True)
    name = Column(String(200), nullable=False)
    category = Column(String(80), nullable=False)
    unit_cost = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    shelf_life_days = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Store(Base):
    __tablename__ = "stores"
    store_id = Column(String(32), primary_key=True)
    name = Column(String(200), nullable=False)
    region = Column(String(80), nullable=False)
    city = Column(String(120), nullable=False)
    size_sqft = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id = Column(String(32), primary_key=True)
    name = Column(String(200), nullable=False)
    region = Column(String(80), nullable=False)
    nominal_lead_time_days = Column(Integer, nullable=False)
    capacity_units_per_day = Column(Integer, nullable=False)
    min_order_qty = Column(Integer, nullable=False, default=0)
    reliability_hint = Column(Float, nullable=False, default=0.9)  # ground-truth marker in synth data
    created_at = Column(DateTime, server_default=func.now())


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(String(32), ForeignKey("suppliers.supplier_id"), nullable=False)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    unit_cost = Column(Float, nullable=False)
    eligible = Column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    store_id = Column(String(32), ForeignKey("stores.store_id"), nullable=False)
    on_hand_units = Column(Integer, nullable=False)
    in_transit_units = Column(Integer, nullable=False, default=0)
    __table_args__ = (
        UniqueConstraint("snapshot_date", "product_id", "store_id", name="uq_inv_snap"),
    )


class SalesTransaction(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    store_id = Column(String(32), ForeignKey("stores.store_id"), nullable=False)
    units_sold = Column(Integer, nullable=False)
    revenue = Column(Float, nullable=False)
    promotion = Column(Boolean, default=False, nullable=False)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_id = Column(String(32), primary_key=True)
    supplier_id = Column(String(32), ForeignKey("suppliers.supplier_id"), nullable=False)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    store_id = Column(String(32), ForeignKey("stores.store_id"), nullable=False)
    units = Column(Integer, nullable=False)
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date, nullable=False)
    actual_delivery_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="OPEN")


class StoreTransfer(Base):
    __tablename__ = "store_transfers"
    transfer_id = Column(String(32), primary_key=True)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    from_store_id = Column(String(32), ForeignKey("stores.store_id"), nullable=False)
    to_store_id = Column(String(32), ForeignKey("stores.store_id"), nullable=False)
    units = Column(Integer, nullable=False)
    created_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="SCHEDULED")


class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    store_id = Column(String(32), ForeignKey("stores.store_id"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    uplift_factor = Column(Float, nullable=False, default=1.0)


class Exception_(Base):
    __tablename__ = "exceptions"
    exception_id = Column(String(32), primary_key=True)
    category = Column(String(64), nullable=False, index=True)
    product_id = Column(String(32), nullable=True, index=True)
    store_id = Column(String(32), nullable=True, index=True)
    supplier_id = Column(String(32), nullable=True, index=True)
    detected_at = Column(DateTime, server_default=func.now())
    severity = Column(String(16), nullable=False)
    risk_score = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    estimated_impact_usd = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="OPEN")
    workflow_hint = Column(String(64), nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    run_id = Column(String(48), primary_key=True)
    exception_id = Column(String(32), ForeignKey("exceptions.exception_id"), nullable=False, index=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    provider = Column(String(32), nullable=False, default="mock")
    model = Column(String(64), nullable=False, default="mock-small")
    status = Column(String(32), nullable=False, default="RUNNING")
    steps = Column(JSON, nullable=False, default=list)
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    cost_estimate_usd = Column(Float, nullable=False, default=0.0)
    error = Column(Text, nullable=True)


class Recommendation(Base):
    __tablename__ = "recommendations"
    recommendation_id = Column(String(32), primary_key=True)
    exception_id = Column(String(32), ForeignKey("exceptions.exception_id"), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    priority = Column(String(16), nullable=False)
    affected_products = Column(JSON, nullable=False, default=list)
    affected_stores = Column(JSON, nullable=False, default=list)
    supporting_evidence = Column(JSON, nullable=False, default=list)
    business_rationale = Column(Text, nullable=False)
    estimated_revenue_at_risk = Column(Float, nullable=False, default=0.0)
    estimated_intervention_cost = Column(Float, nullable=False, default=0.0)
    estimated_net_benefit = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.0)
    assumptions = Column(JSON, nullable=False, default=list)
    constraints = Column(JSON, nullable=False, default=list)
    requires_approval = Column(Boolean, nullable=False, default=True)
    risk_tier = Column(String(16), nullable=False, default="MEDIUM")
    status = Column(String(32), nullable=False, default="PENDING_APPROVAL")
    created_at = Column(DateTime, server_default=func.now())


class ApprovalEvent(Base):
    __tablename__ = "approval_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String(32), ForeignKey("recommendations.recommendation_id"), nullable=False, index=True)
    user = Column(String(80), nullable=False)
    role = Column(String(32), nullable=False)
    decision = Column(String(32), nullable=False)  # APPROVE / REJECT / REQUEST_EVIDENCE
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(48), unique=True, nullable=False)
    event_type = Column(String(80), nullable=False, index=True)
    correlation_id = Column(String(48), nullable=True)
    source = Column(String(64), nullable=False)
    schema_version = Column(String(16), nullable=False, default="1")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    dispatched_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False, default="PENDING")


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(80), nullable=False)
    dataset = Column(String(80), nullable=False)
    received_at = Column(DateTime, server_default=func.now())
    rows_accepted = Column(Integer, nullable=False, default=0)
    rows_rejected = Column(Integer, nullable=False, default=0)
    issues = Column(JSON, nullable=False, default=list)
    source_hash = Column(String(64), nullable=True)
