# Business Problem

## Context
Retail and distribution businesses operate across many stores, products and suppliers. Three recurring failures erode margin:

1. **Stockouts** — product unavailable at the store the customer walks into.
2. **Late deliveries** — supplier commitments slip and the shortage ripples down the chain.
3. **Demand drift** — demand shifts (seasonality, promotion aftershocks, local events) are not reconciled against open POs and current inventory in time to act.

Standard BI shows what already happened. The business needs a system that:

- flags the *next* stockout before it fires,
- isolates *why* it will happen (demand up? supplier late? wrong store received the shipment?),
- proposes a *specific intervention* with a measurable net benefit,
- lets a human approve or reject it with full context,
- and leaves an audit trail suitable for compliance review.

## In scope for this build
- Exception detection, investigation, and recommendation.
- Transparent risk scoring and simulation.
- Human-in-the-loop approval with full history.
- Local, reproducible synthetic dataset.

## Out of scope
- Writing to any real ERP/WMS/OMS. The execution step is simulated by design.
- Live supplier portals, EDI, or carrier APIs.
- Multi-tenant onboarding.
- Live-provider LLM evaluation (the mock provider is used by default).

## Primary KPIs the platform targets
- Reduction in avoidable stockout days.
- Shortened detection-to-decision time for high-severity exceptions.
- Share of recommendations approved on first review (proxy for recommendation quality).
- Share of recommendations with net-benefit > intervention cost.

These are **targets**, not measured outcomes. Measured outcomes against the shipped synthetic dataset are in [`docs/evaluation/`](docs/evaluation/).

---
*Author: **Pradeep Sahoo**.*
