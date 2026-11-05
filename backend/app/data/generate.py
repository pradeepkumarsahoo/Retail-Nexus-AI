# Author: Pradeep Sahoo — Retail Nexus AI
"""Reproducible synthetic retail supply chain dataset generator.

Creates interconnected CSVs for products, stores, suppliers, supplier-product eligibility,
inventory snapshots, daily sales, purchase orders, store transfers, promotions, and
labelled ground-truth events for model evaluation.

Determinism: fixed seed. Marked synthetic in a `_meta.json`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# ---- parameters ------------------------------------------------------------


@dataclass(frozen=True)
class GenParams:
    n_products: int = 100
    n_stores: int = 20
    n_suppliers: int = 10
    days: int = 365
    start_date: date = date(2026, 1, 1)
    seed: int = 42
    categories: tuple[str, ...] = (
        "Grocery",
        "Beverage",
        "Dairy",
        "Snacks",
        "Household",
        "Personal Care",
        "Electronics",
        "Apparel",
    )
    regions: tuple[str, ...] = ("Northeast", "Southeast", "Midwest", "Southwest", "West")


# ---- helpers ---------------------------------------------------------------


def _rand(seed: int) -> tuple[random.Random, np.random.Generator]:
    r = random.Random(seed)
    npr = np.random.default_rng(seed)
    return r, npr


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(row)


# ---- generators ------------------------------------------------------------


def gen_products(p: GenParams, r: random.Random) -> list[dict]:
    out = []
    for i in range(p.n_products):
        pid = f"P{i+1:04d}"
        cat = r.choice(p.categories)
        cost = round(r.uniform(0.5, 80.0), 2)
        price = round(cost * r.uniform(1.3, 2.6), 2)
        shelf = r.choice([None, 14, 30, 60, 180, 365])
        out.append(
            {
                "product_id": pid,
                "name": f"{cat} Item {i+1}",
                "category": cat,
                "unit_cost": cost,
                "unit_price": price,
                "shelf_life_days": shelf if shelf is not None else "",
            }
        )
    return out


def gen_stores(p: GenParams, r: random.Random) -> list[dict]:
    cities = {
        "Northeast": ["Boston", "New York", "Philadelphia", "Hartford"],
        "Southeast": ["Atlanta", "Miami", "Orlando", "Charlotte"],
        "Midwest": ["Chicago", "Detroit", "Minneapolis", "Columbus"],
        "Southwest": ["Dallas", "Houston", "Phoenix", "San Antonio"],
        "West": ["Los Angeles", "Seattle", "Denver", "San Francisco"],
    }
    out = []
    for i in range(p.n_stores):
        sid = f"S{i+1:03d}"
        region = p.regions[i % len(p.regions)]
        city = r.choice(cities[region])
        size = r.choice([8000, 12000, 18000, 25000, 32000])
        out.append(
            {
                "store_id": sid,
                "name": f"Store #{i+1} {city}",
                "region": region,
                "city": city,
                "size_sqft": size,
            }
        )
    return out


def gen_suppliers(p: GenParams, r: random.Random, products: list[dict]) -> tuple[list[dict], list[dict]]:
    suppliers: list[dict] = []
    sup_products: list[dict] = []
    for i in range(p.n_suppliers):
        sid = f"SUP{i+1:03d}"
        lead = r.choice([3, 5, 7, 10, 14, 21])
        cap = r.choice([2000, 5000, 8000, 12000, 20000])
        moq = r.choice([0, 50, 100, 250, 500])
        # Explicit ground-truth: 2 of the 10 are flaky suppliers (lower reliability).
        reliability = 0.60 if i in (3, 7) else r.uniform(0.85, 0.98)
        region = p.regions[i % len(p.regions)]
        suppliers.append(
            {
                "supplier_id": sid,
                "name": f"Supplier {chr(65+i)} Inc.",
                "region": region,
                "nominal_lead_time_days": lead,
                "capacity_units_per_day": cap,
                "min_order_qty": moq,
                "reliability_hint": round(reliability, 3),
            }
        )
        # Each supplier can supply ~40% of products at a cost markup.
        for prod in products:
            if r.random() < 0.4:
                markup = r.uniform(0.9, 1.2)
                sup_products.append(
                    {
                        "supplier_id": sid,
                        "product_id": prod["product_id"],
                        "unit_cost": round(float(prod["unit_cost"]) * markup, 2),
                        "eligible": True,
                    }
                )
    # Guarantee every product has at least one eligible supplier.
    by_prod = {p["product_id"]: [] for p in products}
    for sp in sup_products:
        by_prod[sp["product_id"]].append(sp)
    for prod in products:
        if not by_prod[prod["product_id"]]:
            sup = suppliers[r.randrange(len(suppliers))]
            sup_products.append(
                {
                    "supplier_id": sup["supplier_id"],
                    "product_id": prod["product_id"],
                    "unit_cost": round(float(prod["unit_cost"]) * 1.05, 2),
                    "eligible": True,
                }
            )
    return suppliers, sup_products


def _seasonal_demand(day_idx: int, base: float, season_amp: float, weekly_amp: float) -> float:
    yearly = season_amp * math.sin(2 * math.pi * day_idx / 365.0)
    weekly = weekly_amp * math.sin(2 * math.pi * day_idx / 7.0)
    return max(0.0, base + yearly + weekly)


def gen_sales_and_inventory_and_events(
    p: GenParams,
    r: random.Random,
    npr: np.random.Generator,
    products: list[dict],
    stores: list[dict],
    suppliers: list[dict],
    sup_products: list[dict],
) -> dict[str, list]:
    sales: list[dict] = []
    inv_snaps: list[dict] = []
    pos: list[dict] = []
    transfers: list[dict] = []
    promos: list[dict] = []
    labels: list[dict] = []  # ground-truth events for model evaluation

    sup_by_prod: dict[str, list[dict]] = {}
    for sp in sup_products:
        sup_by_prod.setdefault(sp["product_id"], []).append(sp)
    sup_lookup = {s["supplier_id"]: s for s in suppliers}

    # Per product-store base demand
    base_demand = {}
    for prod in products:
        for st in stores:
            base_demand[(prod["product_id"], st["store_id"])] = max(1.0, npr.gamma(2.0, 2.0))

    # Promotions — ~10% of product-stores get a 7-day promotion window somewhere in the year.
    for prod in products:
        for st in stores:
            if r.random() < 0.1:
                start_offset = r.randint(30, p.days - 15)
                start = p.start_date + timedelta(days=start_offset)
                promos.append(
                    {
                        "product_id": prod["product_id"],
                        "store_id": st["store_id"],
                        "start_date": start.isoformat(),
                        "end_date": (start + timedelta(days=6)).isoformat(),
                        "uplift_factor": round(r.uniform(1.4, 2.5), 2),
                    }
                )

    # Supply disruption windows: for the two flaky suppliers, add a 10-day region shock.
    disruptions: list[tuple[str, int, int]] = []
    for sup in suppliers:
        if sup["reliability_hint"] < 0.7:
            start = r.randint(80, p.days - 60)
            disruptions.append((sup["region"], start, start + 10))
            labels.append(
                {
                    "event_type": "REGIONAL_DISRUPTION",
                    "region": sup["region"],
                    "start_day": start,
                    "end_day": start + 10,
                    "supplier_id": sup["supplier_id"],
                }
            )

    # On-hand inventory starting state
    inv_state: dict[tuple[str, str], float] = {}
    for prod in products:
        for st in stores:
            inv_state[(prod["product_id"], st["store_id"])] = max(
                10.0, base_demand[(prod["product_id"], st["store_id"])] * 14.0
            )

    # Scheduled replenishment plan — simple reorder point policy
    po_counter = 1

    # Precompute promo lookup
    promo_lookup: dict[tuple[str, str], list[tuple[date, date, float]]] = {}
    for pr in promos:
        key = (pr["product_id"], pr["store_id"])
        promo_lookup.setdefault(key, []).append(
            (
                date.fromisoformat(pr["start_date"]),
                date.fromisoformat(pr["end_date"]),
                float(pr["uplift_factor"]),
            )
        )

    # Demand spike/decline injections — labelled ground truth for anomaly eval.
    anomaly_events: list[tuple[str, str, int, float, str]] = []
    for _ in range(60):  # ~60 anomaly events across the year
        prod = r.choice(products)
        st = r.choice(stores)
        day = r.randint(14, p.days - 2)
        if r.random() < 0.5:
            factor = r.uniform(2.5, 4.0)
            kind = "DEMAND_SPIKE"
        else:
            factor = r.uniform(0.1, 0.4)
            kind = "DEMAND_DECLINE"
        anomaly_events.append((prod["product_id"], st["store_id"], day, factor, kind))
        labels.append(
            {
                "event_type": kind,
                "product_id": prod["product_id"],
                "store_id": st["store_id"],
                "day": day,
                "factor": round(factor, 2),
            }
        )
    anomaly_lookup: dict[tuple[str, str, int], float] = {
        (pid, sid, d): f for pid, sid, d, f, _ in anomaly_events
    }

    # Pre-seed some open POs that are late (labelled)
    for _ in range(40):
        prod = r.choice(products)
        st = r.choice(stores)
        sup_options = sup_by_prod.get(prod["product_id"], [])
        if not sup_options:
            continue
        sup_opt = r.choice(sup_options)
        sup = sup_lookup[sup_opt["supplier_id"]]
        order_day = r.randint(0, p.days - 30)
        order_date = p.start_date + timedelta(days=order_day)
        lead = sup["nominal_lead_time_days"]
        expected = order_date + timedelta(days=lead)
        # Is this supplier reliable? Draw actual delivery with slip based on reliability.
        slip = max(0, int(npr.normal(0, (1.0 - sup["reliability_hint"]) * 12)))
        actual = expected + timedelta(days=slip)
        status = "DELIVERED" if actual <= p.start_date + timedelta(days=p.days - 1) else "OPEN"
        pos.append(
            {
                "po_id": f"PO{po_counter:06d}",
                "supplier_id": sup["supplier_id"],
                "product_id": prod["product_id"],
                "store_id": st["store_id"],
                "units": int(max(50, npr.normal(500, 150))),
                "order_date": order_date.isoformat(),
                "expected_delivery_date": expected.isoformat(),
                "actual_delivery_date": actual.isoformat() if status == "DELIVERED" else "",
                "status": status,
            }
        )
        if slip > 2:
            labels.append(
                {
                    "event_type": "SUPPLIER_DELAY",
                    "po_id": f"PO{po_counter:06d}",
                    "supplier_id": sup["supplier_id"],
                    "slip_days": slip,
                }
            )
        po_counter += 1

    # Day loop
    for d in range(p.days):
        day = p.start_date + timedelta(days=d)
        for prod in products:
            for st in stores:
                key = (prod["product_id"], st["store_id"])
                base = base_demand[key]
                mu = _seasonal_demand(d, base, season_amp=base * 0.25, weekly_amp=base * 0.15)
                # Promo?
                mu_eff = mu
                is_promo = False
                for s, e, uplift in promo_lookup.get(key, []):
                    if s <= day <= e:
                        mu_eff *= uplift
                        is_promo = True
                        break
                # Anomaly injection
                if (*key, d) in anomaly_lookup:
                    mu_eff *= anomaly_lookup[(prod["product_id"], st["store_id"], d)]
                # Realized demand
                realized = max(0, int(npr.poisson(mu_eff)))
                # Clamp to inventory on hand
                on_hand = inv_state[key]
                sold = min(realized, int(on_hand))
                lost = realized - sold
                if lost > 0 and d >= 7:
                    labels.append(
                        {
                            "event_type": "LOST_SALES",
                            "product_id": prod["product_id"],
                            "store_id": st["store_id"],
                            "day": d,
                            "units": lost,
                        }
                    )
                revenue = round(sold * float(prod["unit_price"]), 2)
                sales.append(
                    {
                        "sale_date": day.isoformat(),
                        "product_id": prod["product_id"],
                        "store_id": st["store_id"],
                        "units_sold": sold,
                        "revenue": revenue,
                        "promotion": is_promo,
                    }
                )
                inv_state[key] = on_hand - sold
                # Reorder policy — if days-of-supply < 7, place a PO.
                dos = (inv_state[key] / max(1.0, mu)) if mu > 0 else 999
                if dos < 7 and r.random() < 0.3:
                    sup_opts = sup_by_prod.get(prod["product_id"], [])
                    if sup_opts:
                        sup_opt = r.choice(sup_opts)
                        sup = sup_lookup[sup_opt["supplier_id"]]
                        qty = int(max(sup["min_order_qty"], mu * 21))
                        lead = sup["nominal_lead_time_days"]
                        # If a disruption is in effect, extend lead time.
                        for region, s0, s1 in disruptions:
                            if sup["region"] == region and s0 <= d <= s1:
                                lead += r.randint(5, 15)
                        expected = day + timedelta(days=lead)
                        # Did the delivery actually happen before the end of our horizon?
                        slip = max(0, int(npr.normal(0, (1.0 - sup["reliability_hint"]) * 8)))
                        actual = expected + timedelta(days=slip)
                        status = (
                            "DELIVERED" if actual <= p.start_date + timedelta(days=p.days - 1) else "OPEN"
                        )
                        pos.append(
                            {
                                "po_id": f"PO{po_counter:06d}",
                                "supplier_id": sup["supplier_id"],
                                "product_id": prod["product_id"],
                                "store_id": st["store_id"],
                                "units": qty,
                                "order_date": day.isoformat(),
                                "expected_delivery_date": expected.isoformat(),
                                "actual_delivery_date": actual.isoformat() if status == "DELIVERED" else "",
                                "status": status,
                            }
                        )
                        po_counter += 1
                # Deliveries landing today add to inventory
                # (handled below in a sweep for efficiency)
            # end stores
        # Apply any PO deliveries landing today
        for po in pos:
            if po["status"] != "DELIVERED":
                continue
            actual = po["actual_delivery_date"]
            if actual == day.isoformat():
                key = (po["product_id"], po["store_id"])
                inv_state[key] = inv_state.get(key, 0.0) + float(po["units"])
        # Weekly snapshots
        if d % 7 == 0:
            for prod in products:
                for st in stores:
                    key = (prod["product_id"], st["store_id"])
                    on_hand = max(0, int(inv_state[key]))
                    in_transit = sum(
                        int(po["units"])
                        for po in pos
                        if po["status"] in ("OPEN", "DELIVERED")
                        and po["product_id"] == prod["product_id"]
                        and po["store_id"] == st["store_id"]
                        and po["order_date"] <= day.isoformat()
                        and (po["actual_delivery_date"] == "" or po["actual_delivery_date"] > day.isoformat())
                    )
                    inv_snaps.append(
                        {
                            "snapshot_date": day.isoformat(),
                            "product_id": prod["product_id"],
                            "store_id": st["store_id"],
                            "on_hand_units": on_hand,
                            "in_transit_units": in_transit,
                        }
                    )

    # A handful of store transfers (synthetic)
    for i in range(40):
        prod = r.choice(products)
        a, b = r.sample(stores, 2)
        day = p.start_date + timedelta(days=r.randint(30, p.days - 2))
        transfers.append(
            {
                "transfer_id": f"T{i+1:05d}",
                "product_id": prod["product_id"],
                "from_store_id": a["store_id"],
                "to_store_id": b["store_id"],
                "units": r.randint(20, 200),
                "created_date": day.isoformat(),
                "status": "COMPLETED",
            }
        )

    return {
        "sales": sales,
        "inventory": inv_snaps,
        "pos": pos,
        "transfers": transfers,
        "promos": promos,
        "labels": labels,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else _default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    p = GenParams(seed=args.seed, days=args.days)
    r, npr = _rand(p.seed)

    products = gen_products(p, r)
    stores = gen_stores(p, r)
    suppliers, sup_products = gen_suppliers(p, r, products)
    frames = gen_sales_and_inventory_and_events(p, r, npr, products, stores, suppliers, sup_products)

    _write_csv(out_dir / "products.csv", list(products[0].keys()), [list(x.values()) for x in products])
    _write_csv(out_dir / "stores.csv", list(stores[0].keys()), [list(x.values()) for x in stores])
    _write_csv(out_dir / "suppliers.csv", list(suppliers[0].keys()), [list(x.values()) for x in suppliers])
    _write_csv(
        out_dir / "supplier_products.csv",
        list(sup_products[0].keys()),
        [list(x.values()) for x in sup_products],
    )
    _write_csv(
        out_dir / "sales.csv", list(frames["sales"][0].keys()), [list(x.values()) for x in frames["sales"]]
    )
    _write_csv(
        out_dir / "inventory.csv",
        list(frames["inventory"][0].keys()),
        [list(x.values()) for x in frames["inventory"]],
    )
    _write_csv(
        out_dir / "purchase_orders.csv",
        list(frames["pos"][0].keys()),
        [list(x.values()) for x in frames["pos"]],
    )
    _write_csv(
        out_dir / "store_transfers.csv",
        list(frames["transfers"][0].keys()),
        [list(x.values()) for x in frames["transfers"]],
    )
    if frames["promos"]:
        _write_csv(
            out_dir / "promotions.csv",
            list(frames["promos"][0].keys()),
            [list(x.values()) for x in frames["promos"]],
        )
    _write_csv(
        out_dir / "labels_ground_truth.csv",
        ["event_type", "payload"],
        [
            [row["event_type"], json.dumps({k: v for k, v in row.items() if k != "event_type"})]
            for row in frames["labels"]
        ],
    )
    meta = {
        "synthetic": True,
        "seed": p.seed,
        "generated_at": date.today().isoformat(),
        "start_date": p.start_date.isoformat(),
        "days": p.days,
        "n_products": p.n_products,
        "n_stores": p.n_stores,
        "n_suppliers": p.n_suppliers,
        "notes": "Synthetic dataset — not real customer data.",
    }
    (out_dir / "_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote synthetic dataset to {out_dir} (seed={p.seed}, days={p.days})")


def _default_out_dir() -> Path:
    here = Path(__file__).resolve().parent
    # backend/app/data -> repo root/data/synthetic
    return (here.parent.parent.parent / "data" / "synthetic").resolve()


if __name__ == "__main__":
    main()
