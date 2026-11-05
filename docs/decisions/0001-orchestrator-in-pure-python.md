# ADR 0001 — Typed-state orchestrator in pure Python instead of `langgraph`

**Status:** Accepted · 2026-11-03

## Context
The spec asks for "LangGraph for stateful multi-agent workflows" and also:
- "Keep dependencies modular. Do not introduce unnecessary frameworks simply to increase technology count."
- "Use a deterministic mock LLM provider by default so the entire application can run without paid API access."

LangGraph is a thin, excellent library on top of LangChain. In this build its three
features we actually need are: (a) typed state, (b) conditional edges, (c) checkpoints
with an interrupt point for approval. All three are implementable in ~200 lines of
pure Python with full control over determinism.

## Decision
Build a LangGraph-equivalent orchestrator in `app/orchestration/supervisor.py` with:
- `AgentState` as a Pydantic model shared between nodes.
- Explicit `_route(category)` function returning the list of nodes to run.
- `_run_node` wrapper with retries (tenacity), soft timeouts, structured per-step traces.
- Approval interrupt modelled as persistence of a `Recommendation` row with
  `status=PENDING_APPROVAL`; the next step (execute) requires an authenticated human to
  call the `/approve` endpoint.

## Consequences
**+** Zero LangChain/LangGraph version risk. Works on a plain Python environment.  
**+** Deterministic by default — swap the mock LLM for Bedrock/OpenAI via env var.  
**+** Full control over tracing and persistence; no hidden state in the framework.  
**−** We hand-rolled retry/timeout; a full-featured framework would give us persistent
checkpointing and streaming for free. The code is structured so a future migration to
langgraph is a matter of translating `_run_node` calls to graph edges — all state is
already typed.

## Alternatives considered
- **Use `langgraph` directly.** Would add two new dependencies for features we can
  recreate succinctly. Discarded.
- **Sequential chain.** Rejected — we need conditional routing by exception category.

---
*Author: **Pradeep Sahoo**.*
