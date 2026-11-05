# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter

from . import agents, analytics, auth, catalog, data, exceptions, health, recommendations, simulations

router = APIRouter()

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(exceptions.router)
router.include_router(recommendations.router)
router.include_router(simulations.router)
router.include_router(catalog.router)
router.include_router(analytics.router)
router.include_router(agents.router)
router.include_router(data.router)
