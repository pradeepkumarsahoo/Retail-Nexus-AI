# ADR 0005 — Python/FastAPI API vs C#/.NET Core

**Status:** Accepted · 2026-11-03

## Context
The project spec lists FastAPI, Pydantic and a Python-first backend throughout. Section
11 then states: *"REST API will be in C# Code, .NET Core."* This is contradictory with
the rest of the spec: the agents, the ML pipelines, the ingestion validators, and the
OpenAPI expectations are all Python-native.

## Decision
Build the primary REST API in **Python/FastAPI** as the dominant specification
implies. The REST contract is documented via the generated OpenAPI 3.1 schema at
`/openapi.json` and `/docs`. A C#/.NET Core reimplementation of the same contract is
scoped as future work — the OpenAPI schema is the source of truth, so a .NET port can
auto-generate controllers from it.

## Trade-off
Building two API stacks over the same business logic would double the surface, require
cross-process calls between .NET and Python for the ML/agent code, and would not add
any working capability within the time budget. A single Python API, one language for
the whole system, is simpler and more testable.

## If a .NET port is required
- Take the OpenAPI schema produced by this repo's FastAPI app.
- Generate controllers with `nswag` or `openapi-generator` into a new `backend-dotnet/`
  project.
- Have the .NET layer call the Python service for ML/agent endpoints, or port the
  deterministic math only (ML/agent code is out of scope for a .NET rewrite).

---
*Author: **Pradeep Sahoo**.*
