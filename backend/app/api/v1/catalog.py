# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.ml.features import supplier_delivery_stats
from app.models import orm
from app.repositories import frames as fr
from app.schemas.common import ProductOut, StoreOut, SupplierOut, SupplierPerformance
from app.security.auth import User, current_user

router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
def list_products(session: Session = Depends(get_session), user: User = Depends(current_user)) -> list[ProductOut]:
    rows = session.execute(select(orm.Product).order_by(orm.Product.product_id)).scalars().all()
    return [ProductOut.model_validate(r) for r in rows]


@router.get("/stores", response_model=list[StoreOut])
def list_stores(session: Session = Depends(get_session), user: User = Depends(current_user)) -> list[StoreOut]:
    rows = session.execute(select(orm.Store).order_by(orm.Store.store_id)).scalars().all()
    return [StoreOut.model_validate(r) for r in rows]


@router.get("/suppliers", response_model=list[SupplierPerformance])
def list_suppliers(session: Session = Depends(get_session), user: User = Depends(current_user)) -> list[SupplierPerformance]:
    rows = session.execute(select(orm.Supplier).order_by(orm.Supplier.supplier_id)).scalars().all()
    pos = fr.po_frame(session)
    out: list[SupplierPerformance] = []
    for s in rows:
        stats = supplier_delivery_stats(pos, s.supplier_id)
        out.append(SupplierPerformance(
            supplier_id=s.supplier_id, name=s.name,
            on_time_delivery_pct=stats["on_time_delivery_pct"],
            avg_lead_time_days=stats["avg_lead_time_days"],
            lead_time_variance=stats["lead_time_variance"],
            late_po_count=stats["late_po_count"],
            total_po_count=stats["total_po_count"],
            capacity_units_per_day=s.capacity_units_per_day,
        ))
    return out
