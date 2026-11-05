# Author: Pradeep Sahoo — Retail Nexus AI
"""Repository helpers that return pandas frames for the ML/exception layer.

Caches frames in-process for the lifetime of a request; cheap for this scale.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import orm


def sales_frame(session: Session) -> pd.DataFrame:
    stmt = select(
        orm.SalesTransaction.sale_date,
        orm.SalesTransaction.product_id,
        orm.SalesTransaction.store_id,
        orm.SalesTransaction.units_sold,
        orm.SalesTransaction.revenue,
        orm.SalesTransaction.promotion,
    )
    return pd.DataFrame(session.execute(stmt).mappings().all())


def inventory_frame(session: Session) -> pd.DataFrame:
    stmt = select(
        orm.InventorySnapshot.snapshot_date,
        orm.InventorySnapshot.product_id,
        orm.InventorySnapshot.store_id,
        orm.InventorySnapshot.on_hand_units,
        orm.InventorySnapshot.in_transit_units,
    )
    return pd.DataFrame(session.execute(stmt).mappings().all())


def po_frame(session: Session) -> pd.DataFrame:
    stmt = select(
        orm.PurchaseOrder.po_id,
        orm.PurchaseOrder.supplier_id,
        orm.PurchaseOrder.product_id,
        orm.PurchaseOrder.store_id,
        orm.PurchaseOrder.units,
        orm.PurchaseOrder.order_date,
        orm.PurchaseOrder.expected_delivery_date,
        orm.PurchaseOrder.actual_delivery_date,
        orm.PurchaseOrder.status,
    )
    return pd.DataFrame(session.execute(stmt).mappings().all())


def supplier_product_frame(session: Session) -> pd.DataFrame:
    stmt = select(
        orm.SupplierProduct.supplier_id,
        orm.SupplierProduct.product_id,
        orm.SupplierProduct.unit_cost,
        orm.SupplierProduct.eligible,
    )
    return pd.DataFrame(session.execute(stmt).mappings().all())


def product_dict(session: Session) -> dict[str, dict]:
    rows = session.execute(select(orm.Product)).scalars().all()
    return {
        p.product_id: {
            "product_id": p.product_id,
            "name": p.name,
            "category": p.category,
            "unit_cost": p.unit_cost,
            "unit_price": p.unit_price,
            "shelf_life_days": p.shelf_life_days,
        }
        for p in rows
    }


def store_dict(session: Session) -> dict[str, dict]:
    rows = session.execute(select(orm.Store)).scalars().all()
    return {
        s.store_id: {
            "store_id": s.store_id,
            "name": s.name,
            "region": s.region,
            "city": s.city,
            "size_sqft": s.size_sqft,
        }
        for s in rows
    }


def supplier_dict(session: Session) -> dict[str, dict]:
    rows = session.execute(select(orm.Supplier)).scalars().all()
    return {
        s.supplier_id: {
            "supplier_id": s.supplier_id,
            "name": s.name,
            "region": s.region,
            "nominal_lead_time_days": s.nominal_lead_time_days,
            "capacity_units_per_day": s.capacity_units_per_day,
            "min_order_qty": s.min_order_qty,
            "reliability_hint": s.reliability_hint,
        }
        for s in rows
    }
