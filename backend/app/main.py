# Author: Pradeep Sahoo — Retail Nexus AI
"""FastAPI entrypoint for the Retail Nexus AI backend."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.db import init_db
from app.core.logging import configure_logging, get_logger
from app.observability.metrics import REQ_COUNT, REQ_LATENCY, metrics_response

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    log.info("startup", version=__version__)
    yield
    log.info("shutdown")


app = FastAPI(
    title="Retail Nexus AI",
    version=__version__,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _metrics(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start
    REQ_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQ_LATENCY.labels(request.method, request.url.path).observe(duration)
    return response


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.error("unhandled_error", path=request.url.path, err=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(v1_router, prefix=settings.api_v1_prefix)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    body, ct = metrics_response()
    return Response(content=body, media_type=ct)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    """Liveness probe: the process is up. Must not depend on external services."""
    return {"status": "ok", "version": __version__}


@app.get("/readyz", include_in_schema=False)
def readyz() -> Response:
    """Readiness probe: dependencies (DB) are reachable and the app can serve traffic."""
    from sqlalchemy import text

    from app.core.db import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - probe failure path
        log.warning("readyz_db_unavailable", err=str(exc))
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": "db"})
    return JSONResponse(status_code=200, content={"status": "ready"})


@app.get("/")
def root() -> dict:
    return {
        "name": "Retail Nexus AI",
        "version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "metrics": "/metrics",
        "healthz": "/healthz",
        "readyz": "/readyz",
        "api_v1_prefix": settings.api_v1_prefix,
    }
