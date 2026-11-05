# ADR 0004 — Postgres outbox + in-process broker, mapped to SQS/SNS

**Status:** Accepted · 2026-11-03

## Context
We need an event-driven path (StockoutRiskDetected, RecommendationApproved, …) with
idempotent consumers and a reliable publishing story. We do not want to run Kafka
locally.

## Decision
- Business transactions write a row to `outbox_events` in the same DB transaction.
- `app/events/bus.py::dispatch_pending` reads PENDING rows and hands them to an
  in-process broker. Consumers deduplicate by `event_id` so replays are safe.
- The `BROKER` interface mirrors a message bus. An AWS adapter (SQS fan-out from SNS,
  EventBridge for cross-system fan-out) is a straight port — see
  [`infrastructure/aws/README.md`](../../infrastructure/aws/README.md).

## When would we justify a real broker?
- Cross-service or cross-tenant fan-out.
- Multi-region replication.
- Back-pressure management when event rate exceeds what a single worker can consume.
- DLQ semantics beyond what a `status` column can reasonably express.

## Consequences
**+** No new infra for local runs.  
**+** Single source of truth — Postgres.  
**−** A single-node system can lose messages if the DB and consumers run in different
processes and the consumer is not restarted properly; mitigated by the idempotent
`event_id`.

---
*Author: **Pradeep Sahoo**.*
