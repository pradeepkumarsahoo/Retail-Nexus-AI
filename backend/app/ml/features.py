# Author: Pradeep Sahoo — Retail Nexus AI
"""Deterministic feature engineering for forecasting, stockout, anomaly and supplier models.

Pure functions over pandas frames. No DB access.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DemandFeatures:
    history: pd.DataFrame      # daily sales for one (product, store)
    recent_sales_7: float
    recent_sales_14: float
    recent_sales_28: float
    mean_daily: float
    std_daily: float
    cv_daily: float            # coefficient of variation
    weekday_profile: list[float]
    season_strength: float
    promotion_days_14: int


def product_store_daily(sales: pd.DataFrame, product_id: str, store_id: str) -> pd.DataFrame:
    """Return a date-indexed DataFrame of daily units for one (product, store)."""
    df = sales[(sales["product_id"] == product_id) & (sales["store_id"] == store_id)].copy()
    if df.empty:
        return pd.DataFrame(columns=["units_sold", "revenue", "promotion"]).rename_axis("sale_date")
    df["sale_date"] = pd.to_datetime(df["sale_date"]).dt.date
    daily = df.groupby("sale_date").agg(units_sold=("units_sold", "sum"),
                                        revenue=("revenue", "sum"),
                                        promotion=("promotion", "max")).sort_index()
    full_idx = pd.date_range(start=min(daily.index), end=max(daily.index), freq="D").date
    daily = daily.reindex(full_idx).fillna({"units_sold": 0, "revenue": 0.0, "promotion": False})
    daily.index.name = "sale_date"
    return daily


def demand_features(hist: pd.DataFrame) -> DemandFeatures:
    if hist.empty:
        return DemandFeatures(
            history=hist, recent_sales_7=0.0, recent_sales_14=0.0, recent_sales_28=0.0,
            mean_daily=0.0, std_daily=0.0, cv_daily=0.0,
            weekday_profile=[0.0] * 7, season_strength=0.0, promotion_days_14=0,
        )
    units = hist["units_sold"].astype(float)
    last_date = hist.index.max()
    def _window(days: int) -> float:
        start = last_date - timedelta(days=days - 1)
        return float(units.loc[units.index >= start].sum())
    mean_daily = float(units.mean())
    std_daily = float(units.std(ddof=0)) if len(units) > 1 else 0.0
    cv = std_daily / mean_daily if mean_daily > 0 else 0.0
    # weekday profile
    dow = pd.Series(units.index).map(lambda d: pd.Timestamp(d).weekday()).to_numpy()
    weekday_profile = [float(units.to_numpy()[dow == i].mean()) if (dow == i).any() else 0.0 for i in range(7)]
    # season strength = std of weekly mean / overall mean
    if mean_daily > 0 and len(units) >= 14:
        weekly = units.rolling(7, min_periods=7).mean().dropna()
        season_strength = float(weekly.std() / mean_daily) if mean_daily > 0 else 0.0
    else:
        season_strength = 0.0
    promo_14 = int(hist["promotion"].astype(bool).tail(14).sum()) if "promotion" in hist.columns else 0
    return DemandFeatures(
        history=hist,
        recent_sales_7=_window(7),
        recent_sales_14=_window(14),
        recent_sales_28=_window(28),
        mean_daily=mean_daily,
        std_daily=std_daily,
        cv_daily=cv,
        weekday_profile=weekday_profile,
        season_strength=season_strength,
        promotion_days_14=promo_14,
    )


def inventory_snapshot_current(inv: pd.DataFrame, product_id: str, store_id: str) -> dict[str, Any]:
    """Return most recent snapshot for a product-store."""
    sub = inv[(inv["product_id"] == product_id) & (inv["store_id"] == store_id)]
    if sub.empty:
        return {"on_hand_units": 0, "in_transit_units": 0, "snapshot_date": None}
    row = sub.sort_values("snapshot_date").iloc[-1]
    return {
        "on_hand_units": int(row["on_hand_units"]),
        "in_transit_units": int(row["in_transit_units"]),
        "snapshot_date": pd.to_datetime(row["snapshot_date"]).date(),
    }


def days_of_supply(on_hand: float, mean_daily_demand: float) -> float:
    if mean_daily_demand <= 0:
        return float("inf")
    return float(on_hand / mean_daily_demand)


def supplier_delivery_stats(pos: pd.DataFrame, supplier_id: str) -> dict[str, Any]:
    sub = pos[pos["supplier_id"] == supplier_id].copy()
    if sub.empty:
        return {
            "supplier_id": supplier_id, "on_time_delivery_pct": 0.0, "avg_lead_time_days": 0.0,
            "lead_time_variance": 0.0, "late_po_count": 0, "total_po_count": 0,
        }
    sub["expected_delivery_date"] = pd.to_datetime(sub["expected_delivery_date"])
    sub["order_date"] = pd.to_datetime(sub["order_date"])
    delivered = sub[sub["status"] == "DELIVERED"].copy()
    if not delivered.empty:
        delivered["actual_delivery_date"] = pd.to_datetime(delivered["actual_delivery_date"])
        delivered["lead_time"] = (delivered["actual_delivery_date"] - delivered["order_date"]).dt.days
        delivered["slip"] = (delivered["actual_delivery_date"] - delivered["expected_delivery_date"]).dt.days
        on_time = int((delivered["slip"] <= 1).sum())
        otd = on_time / max(1, len(delivered))
        avg_lead = float(delivered["lead_time"].mean())
        lt_var = float(delivered["lead_time"].var(ddof=0))
        late_po = int((delivered["slip"] > 1).sum())
    else:
        otd = 0.0
        avg_lead = 0.0
        lt_var = 0.0
        late_po = 0
    return {
        "supplier_id": supplier_id,
        "on_time_delivery_pct": round(otd, 4),
        "avg_lead_time_days": round(avg_lead, 2),
        "lead_time_variance": round(lt_var, 2),
        "late_po_count": late_po,
        "total_po_count": int(len(sub)),
    }
