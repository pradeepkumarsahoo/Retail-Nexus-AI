# Author: Pradeep Sahoo — Retail Nexus AI
"""Allow-listed tools that agents may call.

Each tool is a plain Python function that reads from the ORM/data layer. Arguments
are validated against `app.security.sanitize.validate_tool_call` before invocation,
so an LLM that tries to invent arguments gets a clear error back.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.ml.features import (
    days_of_supply,
    demand_features,
    inventory_snapshot_current,
    product_store_daily,
    supplier_delivery_stats,
)
from app.ml.forecasting.forecast import gbm_forecast, seasonal_naive
from app.ml.stockout.model import predict as predict_stockout
from app.ml.supplier.risk import score as score_supplier_risk
from app.repositories import frames as fr
from app.security.sanitize import validate_tool_call


def _frames(session: Session) -> dict[str, pd.DataFrame]:
    return {
        "sales": fr.sales_frame(session),
        "inv": fr.inventory_frame(session),
        "pos": fr.po_frame(session),
        "sp": fr.supplier_product_frame(session),
    }


def _dicts(session: Session) -> dict[str, dict]:
    return {
        "products": fr.product_dict(session),
        "stores": fr.store_dict(session),
        "suppliers": fr.supplier_dict(session),
    }


def lookup_product(session: Session, product_id: str) -> dict:
    args = validate_tool_call("lookup_product", {"product_id": product_id})
    products = fr.product_dict(session)
    return products.get(args["product_id"], {})


def lookup_store(session: Session, store_id: str) -> dict:
    args = validate_tool_call("lookup_store", {"store_id": store_id})
    return fr.store_dict(session).get(args["store_id"], {})


def lookup_supplier(session: Session, supplier_id: str) -> dict:
    args = validate_tool_call("lookup_supplier", {"supplier_id": supplier_id})
    return fr.supplier_dict(session).get(args["supplier_id"], {})


def forecast_demand(session: Session, product_id: str, store_id: str, horizon_days: int = 14) -> dict:
    args = validate_tool_call(
        "forecast_demand", {"product_id": product_id, "store_id": store_id, "horizon_days": horizon_days}
    )
    frames = _frames(session)
    hist = product_store_daily(frames["sales"], args["product_id"], args["store_id"])
    if hist.empty:
        return {
            "product_id": args["product_id"],
            "store_id": args["store_id"],
            "forecast": [],
            "model": "none",
        }
    feat = demand_features(hist)
    preds = (
        gbm_forecast(hist, args["horizon_days"])
        if len(hist) >= 60
        else seasonal_naive(hist, args["horizon_days"])
    )
    return {
        "product_id": args["product_id"],
        "store_id": args["store_id"],
        "model": "gbm" if len(hist) >= 60 else "seasonal_naive",
        "mean_daily": round(feat.mean_daily, 3),
        "demand_cv": round(feat.cv_daily, 3),
        "promotion_days_14": feat.promotion_days_14,
        "forecast": [{"date": d.isoformat(), "units": round(float(v), 3)} for d, v in preds],
    }


def stockout_probability(session: Session, product_id: str, store_id: str, horizon_days: int = 14) -> dict:
    args = validate_tool_call(
        "stockout_probability", {"product_id": product_id, "store_id": store_id, "horizon_days": horizon_days}
    )
    frames = _frames(session)
    hist = product_store_daily(frames["sales"], args["product_id"], args["store_id"])
    inv_now = inventory_snapshot_current(frames["inv"], args["product_id"], args["store_id"])
    incoming = int(
        frames["pos"][
            (frames["pos"]["product_id"] == args["product_id"])
            & (frames["pos"]["store_id"] == args["store_id"])
            & (frames["pos"]["status"] == "OPEN")
        ]["units"].sum()
    )
    sp = frames["sp"]
    sup_ids = sp[(sp["product_id"] == args["product_id"]) & sp["eligible"]]["supplier_id"].tolist()
    otd = (
        float(np.mean([supplier_delivery_stats(frames["pos"], s)["on_time_delivery_pct"] for s in sup_ids]))
        if sup_ids
        else 0.9
    )
    pred = predict_stockout(
        hist,
        inv_now,
        args["product_id"],
        args["store_id"],
        horizon_days=args["horizon_days"],
        incoming_po_units=incoming,
        supplier_otd=otd,
    )
    return {
        "product_id": pred.product_id,
        "store_id": pred.store_id,
        "horizon_days": pred.horizon_days,
        "probability": pred.probability,
        "predicted_stockout_date": pred.predicted_stockout_date.isoformat()
        if pred.predicted_stockout_date
        else None,
        "risk_category": pred.risk_category,
        "suggested_action": pred.suggested_action,
        "data": pred.data,
        "contributing_factors": [f.__dict__ for f in pred.contributing_factors],
        "supplier_otd_avg": round(otd, 3),
    }


def supplier_reliability(session: Session, supplier_id: str) -> dict:
    args = validate_tool_call("supplier_reliability", {"supplier_id": supplier_id})
    frames = _frames(session)
    r = score_supplier_risk(frames["pos"], args["supplier_id"])
    return {
        "supplier_id": r.supplier_id,
        "risk_score": r.risk_score,
        "risk_category": r.risk_category,
        "factors": [f.__dict__ for f in r.factors],
        "stats": r.stats,
    }


def find_alt_suppliers(session: Session, product_id: str) -> dict:
    args = validate_tool_call("find_alt_suppliers", {"product_id": product_id})
    frames = _frames(session)
    sp = frames["sp"]
    suppliers = _dicts(session)["suppliers"]
    rows = sp[(sp["product_id"] == args["product_id"]) & sp["eligible"]]
    alts: list[dict] = []
    for _, r in rows.iterrows():
        sid = r["supplier_id"]
        info = suppliers.get(sid, {})
        if not info:
            continue
        stats = supplier_delivery_stats(frames["pos"], sid)
        alts.append(
            {
                "supplier_id": sid,
                "name": info.get("name"),
                "lead_time_days": info.get("nominal_lead_time_days"),
                "capacity_units_per_day": info.get("capacity_units_per_day"),
                "min_order_qty": info.get("min_order_qty"),
                "unit_cost": float(r["unit_cost"]),
                "on_time_delivery_pct": stats["on_time_delivery_pct"],
                "avg_lead_time_days": stats["avg_lead_time_days"],
            }
        )
    alts.sort(key=lambda a: (-a["on_time_delivery_pct"], a["lead_time_days"], a["unit_cost"]))
    return {"product_id": args["product_id"], "alternatives": alts}


def find_transfer_candidates(session: Session, product_id: str, store_id: str) -> dict:
    args = validate_tool_call("find_transfer_candidates", {"product_id": product_id, "store_id": store_id})
    frames = _frames(session)
    inv = frames["inv"]
    stores = _dicts(session)["stores"]
    # Current on-hand for each store for this product
    latest = inv[inv["product_id"] == args["product_id"]].sort_values("snapshot_date")
    if latest.empty:
        return {"candidates": []}
    latest_by_store = latest.groupby("store_id").tail(1)
    sales = frames["sales"]
    cands: list[dict] = []
    for _, row in latest_by_store.iterrows():
        sid = row["store_id"]
        if sid == args["store_id"]:
            continue
        hist = product_store_daily(sales, args["product_id"], sid)
        feat = demand_features(hist)
        dos = days_of_supply(float(row["on_hand_units"]), feat.mean_daily) if feat.mean_daily > 0 else 999
        # Candidate must have DoS > 30 to be a source
        if dos > 30 and float(row["on_hand_units"]) > 20:
            cands.append(
                {
                    "from_store_id": sid,
                    "from_store_name": stores.get(sid, {}).get("name"),
                    "available_units": int(row["on_hand_units"]),
                    "donor_days_of_supply": round(float(dos), 1),
                    "donor_mean_daily_demand": round(feat.mean_daily, 2),
                }
            )
    cands.sort(key=lambda c: (-c["available_units"], -c["donor_days_of_supply"]))
    return {"candidates": cands[:10]}


TOOLS = {
    "lookup_product": lookup_product,
    "lookup_store": lookup_store,
    "lookup_supplier": lookup_supplier,
    "forecast_demand": forecast_demand,
    "stockout_probability": stockout_probability,
    "supplier_reliability": supplier_reliability,
    "find_alt_suppliers": find_alt_suppliers,
    "find_transfer_candidates": find_transfer_candidates,
}
