# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.data.load import (
    POrow, ProductRow, PromotionRow, SaleRow, StoreRow, SupplierProductRow, SupplierRow, TransferRow,
    InventoryRow,
)
from app.models import orm
from app.schemas.common import IngestResult
from app.security.auth import Role, User, current_user, require_roles
from app.security.rate_limit import rate_limited
from pydantic import BaseModel

router = APIRouter()


_SCHEMAS = {
    "products": (ProductRow, orm.Product),
    "stores": (StoreRow, orm.Store),
    "suppliers": (SupplierRow, orm.Supplier),
    "supplier_products": (SupplierProductRow, orm.SupplierProduct),
    "inventory": (InventoryRow, orm.InventorySnapshot),
    "sales": (SaleRow, orm.SalesTransaction),
    "purchase_orders": (POrow, orm.PurchaseOrder),
    "store_transfers": (TransferRow, orm.StoreTransfer),
    "promotions": (PromotionRow, orm.Promotion),
}


MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB cap


def _ingest_rows(session: Session, dataset: str, rows: list[dict[str, Any]], source_name: str, source_hash: str) -> IngestResult:
    if dataset not in _SCHEMAS:
        raise HTTPException(status_code=400, detail=f"Unknown dataset: {dataset}")
    schema, model = _SCHEMAS[dataset]
    accepted: list[dict] = []
    rejected: list[dict] = []
    for i, raw in enumerate(rows, start=1):
        try:
            m = schema.model_validate(raw)
            accepted.append(m.model_dump())
        except Exception as e:
            rejected.append({"row": i, "error": str(e), "raw": raw})
    if accepted:
        session.bulk_insert_mappings(model, accepted)
    session.add(orm.IngestionLog(
        source=source_name, dataset=dataset, rows_accepted=len(accepted),
        rows_rejected=len(rejected), issues=rejected[:50], source_hash=source_hash,
    ))
    session.commit()
    return IngestResult(dataset=dataset, rows_accepted=len(accepted), rows_rejected=len(rejected),
                        issues=rejected[:50], source_hash=source_hash)


class IngestBody(BaseModel):
    dataset: str
    rows: list[dict[str, Any]]


@router.post("/data/ingest", response_model=IngestResult,
             dependencies=[Depends(rate_limited(limit_per_minute=30))])
def ingest_json(
    body: IngestBody,
    session: Session = Depends(get_session),
    user: User = Depends(require_roles(Role.ADMIN, Role.PROCUREMENT, Role.ANALYST)),
) -> IngestResult:
    payload = json.dumps(body.rows, sort_keys=True, default=str).encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    return _ingest_rows(session, body.dataset, body.rows, source_name=f"api:{body.dataset}", source_hash=sha)


@router.post("/data/upload", response_model=IngestResult,
             dependencies=[Depends(rate_limited(limit_per_minute=10))])
async def upload_csv(
    dataset: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(require_roles(Role.ADMIN, Role.PROCUREMENT, Role.ANALYST)),
) -> IngestResult:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_BYTES} bytes")
    sha = hashlib.sha256(data).hexdigest()
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}") from e
    rows = df.to_dict("records")
    return _ingest_rows(session, dataset, rows, source_name=f"upload:{file.filename}", source_hash=sha)
