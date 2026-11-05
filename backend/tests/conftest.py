# Author: Pradeep Sahoo — Retail Nexus AI
"""Shared pytest fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Force a temp SQLite DB per session so tests never touch the dev DB.
_tmp_db = Path(tempfile.mkdtemp(prefix="ct-test-")) / "test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_db.as_posix()}")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-change-me-32-chars-min")
os.environ.setdefault("LLM_PROVIDER", "mock")


@pytest.fixture(scope="session")
def init_test_db() -> None:
    from app.core.db import init_db

    init_db()


@pytest.fixture
def session(init_test_db):
    from app.core.db import SessionLocal

    s = SessionLocal()()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture
def client(init_test_db):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client) -> str:
    r = client.post("/api/v1/auth/token", data={"username": "demo-admin", "password": "demo"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def director_token(client) -> str:
    r = client.post("/api/v1/auth/token", data={"username": "demo-director", "password": "demo"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def analyst_token(client) -> str:
    r = client.post("/api/v1/auth/token", data={"username": "demo-analyst", "password": "demo"})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
