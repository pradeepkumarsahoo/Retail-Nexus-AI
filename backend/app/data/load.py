# Author: Pradeep Sahoo — Retail Nexus AI
"""Load the synthetic CSV dataset into the database.

Validates every row via Pydantic and records ingestion lineage.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import delete, insert

from app.core.db import init_db, session_scope
from app.core.logging import configure_logging, get_logger
from app.models import orm

log = get_logger("data.load")


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    return date.fromisoformat(s)


class ProductRow(BaseModel):
    product_id: str
    name: str
    category: str
    unit_cost: float
    unit_price: float
    shelf_life_days: int | None = None

    @field_validator("shelf_life_days", mode="before")
    @classmethod
    def _blank_to_none(cls, v: Any) -> Any:
        if v in ("", None):
            return None
        return v


class StoreRow(BaseModel):
    store_id: str
    name: str
    region: str
    city: str
    size_sqft: int


class SupplierRow(BaseModel):
    supplier_id: str
    name: str
    region: str
    nominal_lead_time_days: int
    capacity_units_per_day: int
    min_order_qty: int
    reliability_hint: float


class SupplierProductRow(BaseModel):
    supplier_id: str
    product_id: str
    unit_cost: float
    eligible: bool

    @field_validator("eligible", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "y")
        return bool(v)


class SaleRow(BaseModel):
    sale_date: date
    product_id: str
    store_id: str
    units_sold: int
    revenue: float
    promotion: bool

    @field_validator("promotion", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "y")
        return bool(v)


class InventoryRow(BaseModel):
    snapshot_date: date
    product_id: str
    store_id: str
    on_hand_units: int
    in_transit_units: int


class POrow(BaseModel):
    po_id: str
    supplier_id: str
    product_id: str
    store_id: str
    units: int
    order_date: date
    expected_delivery_date: date
    actual_delivery_date: date | None
    status: str

    @field_validator("actual_delivery_date", mode="before")
    @classmethod
    def _blank_to_none(cls, v: Any) -> Any:
        if v in ("", None):
            return None
        return v


class TransferRow(BaseModel):
    transfer_id: str
    product_id: str
    from_store_id: str
    to_store_id: str
    units: int
    created_date: date
    status: str


class PromotionRow(BaseModel):
    product_id: str
    store_id: str | None = None
    start_date: date
    end_date: date
    uplift_factor: float

    @field_validator("store_id", mode="before")
    @classmethod
    def _blank_to_none(cls, v: Any) -> Any:
        if v in ("", None):
            return None
        return v


def _read_csv(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield dict(row.items())


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _bulk_insert(table_cls: Any, rows: list[dict[str, Any]], chunk: int = 1000) -> None:
    if not rows:
        return
    with session_scope() as s:
        for i in range(0, len(rows), chunk):
            s.execute(insert(table_cls), rows[i : i + chunk])


def _wipe_tables() -> None:
    with session_scope() as s:
        for cls in (
            orm.ApprovalEvent,
            orm.Recommendation,
            orm.AgentRun,
            orm.Exception_,
            orm.OutboxEvent,
            orm.StoreTransfer,
            orm.Promotion,
            orm.PurchaseOrder,
            orm.SalesTransaction,
            orm.InventorySnapshot,
            orm.SupplierProduct,
            orm.Supplier,
            orm.Store,
            orm.Product,
            orm.IngestionLog,
        ):
            s.execute(delete(cls))


def _validate_and_collect(path: Path, schema: type[BaseModel]) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    rejected: list[dict] = []
    for i, raw in enumerate(_read_csv(path), start=2):
        try:
            model = schema.model_validate(raw)
            accepted.append(model.model_dump())
        except ValidationError as e:
            rejected.append({"row": i, "errors": json.loads(e.json()), "raw": raw})
    return accepted, rejected


def _log_ingestion(
    dataset: str, source: str, accepted: int, rejected_rows: list[dict], source_hash: str
) -> None:
    with session_scope() as s:
        s.add(
            orm.IngestionLog(
                source=source,
                dataset=dataset,
                rows_accepted=accepted,
                rows_rejected=len(rejected_rows),
                issues=rejected_rows[:50],
                source_hash=source_hash,
            )
        )


def load_all(data_dir: Path, wipe: bool = True) -> dict[str, Any]:
    init_db()
    if wipe:
        _wipe_tables()
    report: dict[str, Any] = {}

    plan = [
        ("products", "products.csv", ProductRow, orm.Product),
        ("stores", "stores.csv", StoreRow, orm.Store),
        ("suppliers", "suppliers.csv", SupplierRow, orm.Supplier),
        ("supplier_products", "supplier_products.csv", SupplierProductRow, orm.SupplierProduct),
        ("inventory", "inventory.csv", InventoryRow, orm.InventorySnapshot),
        ("sales", "sales.csv", SaleRow, orm.SalesTransaction),
        ("purchase_orders", "purchase_orders.csv", POrow, orm.PurchaseOrder),
        ("store_transfers", "store_transfers.csv", TransferRow, orm.StoreTransfer),
        ("promotions", "promotions.csv", PromotionRow, orm.Promotion),
    ]

    for dataset, fname, schema, model_cls in plan:
        path = data_dir / fname
        if not path.exists():
            log.info("skip_missing", dataset=dataset, path=str(path))
            continue
        accepted, rejected = _validate_and_collect(path, schema)
        _bulk_insert(model_cls, accepted)
        src_hash = _hash_file(path)
        _log_ingestion(
            dataset, source=fname, accepted=len(accepted), rejected_rows=rejected, source_hash=src_hash
        )
        report[dataset] = {"accepted": len(accepted), "rejected": len(rejected)}
        log.info("loaded", dataset=dataset, accepted=len(accepted), rejected=len(rejected))
    return report


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--no-wipe", action="store_true")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    default_dir = (here.parent.parent.parent / "data" / "synthetic").resolve()
    data_dir = Path(args.data) if args.data else default_dir
    print(json.dumps(load_all(data_dir, wipe=not args.no_wipe), indent=2))


if __name__ == "__main__":
    main()
