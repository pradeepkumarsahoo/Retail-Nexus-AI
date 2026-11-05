# ADR 0002 — Deterministic math, LLM reasoning (not the other way round)

**Status:** Accepted · 2026-11-03

## Context
LLMs are excellent at interpreting structured evidence and composing a rationale; they
are **not** reliable sources of numbers. A recommendation that a human will approve for
financial impact cannot carry a number the LLM invented.

## Decision
- Every numeric field in a recommendation (revenue-at-risk, intervention cost, net
  benefit, risk score, probability, days-of-supply, OTD, lead-time variance) is produced
  by a deterministic Python function over the data.
- The LLM is asked only to: (a) explain those numbers in prose, (b) report a confidence
  bounded between 0 and 1 derived from the same numbers, (c) choose between
  alternatives using an explicit rubric.
- The orchestrator does not persist any LLM-generated structured field as a decision
  input; it passes evidence by value.

## Consequences
**+** Reproducible under identical inputs. Testable without network.  
**+** Simpler to audit — every number traces to a function in `app/ml/` or
   `app/services/`.  
**−** Less "chattiness" from the agent. Users who want conversational drill-down must
   add a dedicated QA endpoint later.

---
*Author: **Pradeep Sahoo**.*
