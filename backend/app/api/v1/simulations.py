# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.ml.features import inventory_snapshot_current, product_store_daily
from app.models import orm
from app.repositories import frames as fr
from app.schemas.common import ScenarioOutcome, SimulationRequest, SimulationResponse
from app.security.auth import User, current_user
from app.simulation.simulator import run as run_sim

router = APIRouter()


@router.post("/simulations/run", response_model=SimulationResponse)
def run_simulation(
    body: SimulationRequest,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> SimulationResponse:
    exc = session.get(orm.Exception_, body.exception_id)
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    if not exc.product_id or not exc.store_id:
        raise HTTPException(status_code=400, detail="Simulation requires a product/store on the exception")
    sales = fr.sales_frame(session)
    inv = fr.inventory_frame(session)
    hist = product_store_daily(sales, exc.product_id, exc.store_id)
    inv_now = inventory_snapshot_current(inv, exc.product_id, exc.store_id)
    product = fr.product_dict(session).get(exc.product_id, {})
    unit_price = float(product.get("unit_price", 0.0))
    unit_cost = float(product.get("unit_cost", 0.0))
    scenarios = [{"name": s.name, "params": s.params} for s in body.scenarios]
    outcomes = run_sim(exc.evidence or {}, scenarios, hist, inv_now, unit_price, unit_cost, body.horizon_days)
    out_models = [ScenarioOutcome(**o.__dict__) for o in outcomes]
    # Pick recommended = highest net benefit (non-baseline)
    non_baseline = [o for o in out_models if o.scenario != "BASELINE"]
    recommended = max(non_baseline, key=lambda x: x.net_benefit_usd).scenario if non_baseline else "BASELINE"
    return SimulationResponse(
        exception_id=exc.exception_id, horizon_days=body.horizon_days,
        outcomes=out_models, recommended_scenario=recommended,
    )
