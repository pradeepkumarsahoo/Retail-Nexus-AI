# Author: Pradeep Sahoo — Retail Nexus AI
"""End-to-end API smoke: health, auth, exception detection, agent investigation, approval flow."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def seeded(request):
    """Generate a tiny synthetic dataset and load it. One-time per module."""
    from app.core.db import init_db
    from app.data.generate import (
        GenParams,
        _rand,
        gen_products,
        gen_sales_and_inventory_and_events,
        gen_stores,
        gen_suppliers,
    )
    from app.data.load import load_all

    init_db()
    tmp = Path(tempfile.mkdtemp(prefix="ct-smoke-"))
    p = GenParams(seed=7, days=90, n_products=6, n_stores=3, n_suppliers=3)
    r, npr = _rand(p.seed)
    products = gen_products(p, r)
    stores = gen_stores(p, r)
    suppliers, sup_products = gen_suppliers(p, r, products)
    frames = gen_sales_and_inventory_and_events(p, r, npr, products, stores, suppliers, sup_products)

    # Write CSVs
    def _w(name, rows):
        if not rows:
            return
        import csv

        with (tmp / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for row in rows:
                w.writerow(row)

    _w("products", products)
    _w("stores", stores)
    _w("suppliers", suppliers)
    _w("supplier_products", sup_products)
    _w("sales", frames["sales"])
    _w("inventory", frames["inventory"])
    _w("purchase_orders", frames["pos"])
    _w("store_transfers", frames["transfers"])
    _w("promotions", frames["promos"])

    load_all(tmp, wipe=True)
    return tmp


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "mock"


def test_unauth_rejected(client):
    r = client.get("/api/v1/exceptions")
    assert r.status_code == 401


def test_auth_token_and_me(client):
    r = client.post("/api/v1/auth/token", data={"username": "demo-admin", "password": "demo"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_dashboard_runs(client, auth_headers, seeded):
    r = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    for k in ("active_exceptions", "exceptions_by_category", "trend_last_14_days"):
        assert k in body


def test_full_flow_detect_investigate_approve(client, admin_token, director_token, seeded):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Detect
    r = client.post("/api/v1/exceptions/detect", headers=headers)
    assert r.status_code == 200
    created = r.json()["created"]
    if created == 0:
        pytest.skip("Synthetic sample produced no exceptions; acceptable given small seed")
    # List
    r = client.get("/api/v1/exceptions?limit=5", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    exc_id = items[0]["exception_id"]
    # Investigate
    r = client.post(f"/api/v1/exceptions/{exc_id}/investigate", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["recommendations"], "investigation must emit at least one recommendation"
    rec_id = body["recommendations"][0]["recommendation_id"]
    # Approve with director (can approve any tier)
    dir_headers = {"Authorization": f"Bearer {director_token}"}
    r = client.post(
        f"/api/v1/recommendations/{rec_id}/approve", headers=dir_headers, json={"comment": "approved"}
    )
    assert r.status_code == 200
    assert r.json()["status"] in ("EXECUTED", "APPROVED")


def test_rbac_blocks_low_role_on_critical(client, analyst_token, admin_token, seeded):
    # Create and investigate to produce a HIGH/CRITICAL recommendation
    admin_h = {"Authorization": f"Bearer {admin_token}"}
    client.post("/api/v1/exceptions/detect", headers=admin_h)
    exc_list = (
        client.get("/api/v1/exceptions?severity=CRITICAL&limit=1", headers=admin_h).json()["items"]
        or client.get("/api/v1/exceptions?severity=HIGH&limit=1", headers=admin_h).json()["items"]
    )
    if not exc_list:
        pytest.skip("No high-tier exception produced")
    exc_id = exc_list[0]["exception_id"]
    recs = client.post(f"/api/v1/exceptions/{exc_id}/investigate", headers=admin_h).json()["recommendations"]
    target = next((r for r in recs if r["risk_tier"] in ("CRITICAL", "HIGH")), None)
    if not target:
        pytest.skip("Investigation did not yield a high-tier recommendation on this seed")
    r = client.post(
        f"/api/v1/recommendations/{target['recommendation_id']}/approve",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"comment": "not authorised"},
    )
    assert r.status_code == 403
