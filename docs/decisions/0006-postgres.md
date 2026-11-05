# ADR 0006 — PostgreSQL as system of record; SQLite in dev

**Status:** Accepted · 2026-11-03

## Context
We need durable storage for exceptions, agent runs, recommendations, approvals, and
the outbox. Analytical queries (daily demand aggregation, dashboard counts) share the
same engine. We want a smooth dev experience that doesn't require Docker.

## Decision
- Production/staging: **PostgreSQL** (via SQLAlchemy + `psycopg`).
- Local dev without Docker: **SQLite** at `control_tower.db`. SQLAlchemy's dialect
  translation covers everything we need. CI uses Postgres via docker-compose.
- The outbox + domain tables live in the same DB. Separate connection pools are
  unnecessary at this scale.

## Consequences
**+** One schema, one migration path (Alembic).  
**+** SQLite dev loop is instant.  
**−** SQLite does not enforce all FK constraints by default; migrations have been kept
  simple enough that this gap has no effect on tests.

---
*Author: **Pradeep Sahoo**.*
