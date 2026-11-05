# Retail Nexus AI — Enterprise Agentic AI Platform for Retail Intelligence

> **Retail Nexus AI** is an enterprise-oriented Agentic AI platform for retail intelligence, combining **demand forecasting**, **inventory optimization**, and **supply chain exception management** to deliver evidence-backed recommendations, intelligent workflows, and smarter operational decisions. Detect disruptions, investigate them with specialised agents, predict stockouts and supplier delays, simulate corrective actions, and route consequential decisions through human approval. **Every recommendation is evidence-backed and reversible.**

[![backend CI](https://github.com/pradeepsahoo-ms/retail-nexus-ai/actions/workflows/backend.yml/badge.svg)](https://github.com/pradeepsahoo-ms/retail-nexus-ai/actions/workflows/backend.yml)
[![frontend CI](https://github.com/pradeepsahoo-ms/retail-nexus-ai/actions/workflows/frontend.yml/badge.svg)](https://github.com/pradeepsahoo-ms/retail-nexus-ai/actions/workflows/frontend.yml)
[![CodeQL](https://github.com/pradeepsahoo-ms/retail-nexus-ai/actions/workflows/codeql.yml/badge.svg)](https://github.com/pradeepsahoo-ms/retail-nexus-ai/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000.svg)](https://docs.astral.sh/ruff/)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-2a6db2.svg)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](.pre-commit-config.yaml)
[![License: MIT](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-reference--build-orange.svg)]()

> **Project governance:** [LICENSE](LICENSE) · [SECURITY.md](SECURITY.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [CHANGELOG.md](CHANGELOG.md) · [CODEOWNERS](.github/CODEOWNERS)

**Author:** Pradeep Sahoo · Engineering Lead
**Version:** 0.1.0 · **Updated:** 2026-11-04 · **Scope:** Large-scale retail supply chain ecosystem

---

## Table of contents

1. [Executive summary](#executive-summary)
2. [Problem statement](#problem-statement)
3. [Solution overview](#solution-overview)
4. [Key features](#key-features)
5. [System architecture](#system-architecture)
6. [Agent workflow](#agent-workflow)
7. [Security — OWASP Top 7 for LLMs](#security--owasp-top-7-for-llms)
8. [Engineering decisions (ADRs)](#engineering-decisions-adrs)
9. [Technology stack](#technology-stack)
10. [Prerequisites](#prerequisites)
11. [Installation & setup](#installation--setup)
12. [Running the application](#running-the-application)
13. [Configuration](#configuration)
14. [Testing & evaluation](#testing--evaluation)
15. [Repository layout](#repository-layout)
16. [Scale & cost model](#scale--cost-model)
17. [Business impact & revenue potential](#business-impact--revenue-potential)
18. [Deployment reference (AWS)](#deployment-reference-aws)
19. [Production readiness & reliability](#production-readiness--reliability)
20. [AI governance & operating controls](#ai-governance--operating-controls)
21. [Phased transformation roadmap](#phased-transformation-roadmap)
22. [Troubleshooting](#troubleshooting)
23. [Known limitations](#known-limitations)
24. [Contributing](#contributing)
25. [License](#license)
26. [Author](#author)

---

## Executive summary

A large retail operator loses ~**$3-4 B / yr** to five preventable supply-chain failures that today's reporting stack does not address. This platform turns that detection gap into evidence-backed, approvable actions.

| Dimension | Headline |
|---|---|
| **Business challenge** | ~ $3-4 B / yr preventable loss inside one $50 B retailer (stockouts, late suppliers, excess inventory, slow decisions). |
| **Target operating model** | Detect → predict → investigate → simulate → approve. Deterministic math; LLM only explains. |
| **Capabilities** | 4 predictive models · 6 specialist agents · OWASP Top 7 guard per agent · HITL governance. |
| **Modelled value** | **$425 – 720 M / yr** opportunity per Tier-1 retailer · ~ $660 K / yr run cost · ROI 600-1000× · payback < 1 week. |
| **SaaS potential** | $75-150 M year-5 ARR across 50-110 retail logos (hyperscale, enterprise, mid-market). |
| **Unit economics** | $0.018 cost per decision vs $3-6 of margin on one avoided stockout. |
| **Maturity** | Reference build on a synthetic dataset. See maturity key below. |

### Maturity key

| Label | Meaning |
|---|---|
| **Built** | Working code in this repo, exercised by tests on the synthetic dataset. |
| **Simulated** | Implemented against mock / simulated external systems (no live integrations). |
| **Modelled** | Figures derived from public industry benchmarks applied to the scale assumptions. |
| **Planned** | Documented design with acceptance criteria, not yet exercised. |
| **Not built** | Explicitly out of scope (e.g. real ERP connector, continuous retraining). |

---

## Problem statement

Modern retail BI tells operators what already happened — yesterday's stockouts, last week's late trucks. It cannot answer the forward-looking, actionable questions that actually move revenue:

- Which products at which stores will stock out in the next **7 / 14 / 30 days**?
- Which suppliers are statistically likely to deliver late — and which open POs are affected?
- Which demand swings are real spikes vs promotion aftershocks?
- For a given exception, what is the **best** intervention, and what is its net benefit in dollars?
- Who authorised the decision, on what evidence, under which assumptions?

### Cost of inaction (industry benchmarks)

| Signal | Benchmark | Source |
|---|---|---|
| Global stockout losses | **$1.2 T / yr** | IHL Group 2023 |
| Average out-of-stock rate | **8-10 %** | NielsenIQ |
| Excess & aging inventory | **20-30 %** of on-hand | Gartner retail |
| Detection → decision latency | **2-5 days** | Typical BI workflow |

Applied to one $50 B retailer at the scale below: stockouts ≈ $1.5 B, excess carry ≈ $1.25-2 B, expedites ≈ $150-300 M — **6-8 % of revenue** at risk annually.

---

## Solution overview

**Retail Nexus AI** — an enterprise Agentic AI platform that turns raw retail operational data into evidence-backed, approvable actions. Seven layers:

| Layer | Responsibility |
|---|---|
| **A. Ingestion** | CSV + API intake, Pydantic validation, lineage, DQ rules, rejects logged. |
| **B. Processing** | Normalised masters, daily demand aggregates, lead-time / OTD stats, features. |
| **C. Predictive ML** | 4 separate models — demand forecast, stockout, demand anomaly, supplier delay — each against an honest baseline. |
| **D. Exception engine** | 11 categories, 5-factor transparent risk score, labelled severity. |
| **E. Agents** | 6 specialists + supervisor on a typed state machine (LangGraph-equivalent). Deterministic engines compute numbers; LLMs only explain. |
| **F. Decision + HITL** | Schema-complete recommendations, deterministic what-if simulator, role-gated approvals, simulated action adapter. |
| **G. Operations** | Outbox event bus (→ SQS/SNS/EventBridge), OTEL traces, Prometheus metrics, token & cost accounting. |

### Request lifecycle

`Detect → Investigate → Recommend → Approve → Act` (simulated)

1. **Detect** — Scheduled or event-driven exception sweep. Each exception carries a 5-factor risk score and raw evidence.
2. **Investigate** — Supervisor routes to only the agents warranted by the category. Typed state, structured JSON outputs.
3. **Recommend** — Deterministic math produces every number; LLM only explains. Ranked by net benefit. Schema-validated.
4. **Approve** — Role-gated review (Approve · Reject · Request-more-evidence). Full audit trail.
5. **Act** — Simulated adapter emits `ActionExecuted`. No real ERP write — safety by design.

---

## Key features

- **4 predictive models** — demand forecast · stockout classifier · demand anomaly · supplier delay — each measured against an honest baseline.
- **6 specialist agents** + supervisor on a typed state machine. Deterministic engines compute numbers; LLMs only explain.
- **OWASP Top 7 for LLMs** guard wrapped around every agent.
- **Human-in-the-loop governance** — role-gated approvals, full audit trail, simulated action adapter (no ERP write by design).
- **Event-driven backbone** — Postgres outbox → in-proc dispatcher (local) → SNS/SQS/EventBridge (AWS).
- **Mock LLM default** — zero-cost reproducible demos; Bedrock / OpenAI swap via one env var.
- **Explainable risk scoring** — 5-factor transparent score across 11 exception categories.
- **Deterministic what-if simulator** — baseline vs expedite / transfer / switch-supplier / increase-replenishment under explicit formulas.
- **Per-agent cost accounting** — token meter tagged by correlation id.
- **Observability out of the box** — structured JSON logs, OTEL traces, Prometheus `/metrics`, per-run agent tracing.

Sized for **10 k suppliers · 5 k stores · 100 k customers/day · 100 k exceptions/day**.

---

## System architecture

### High-level flow

```
┌───────────┐  ┌───────────┐  ┌──────────────┐  ┌────────────────┐  ┌───────────┐
│ Ingestion │─▶│Processing │─▶│Predictive ML │─▶│Exception Engine│─▶│ Event Bus │
└───────────┘  └───────────┘  └──────────────┘  └────────────────┘  └─────┬─────┘
                                                                          │
                                       ┌──────────────────────────────────┘
                                       ▼
          ┌───────────────────────────────────────────────────────────────┐
          │  LangGraph-equivalent Multi-Agent Workflow (typed state)      │
          │                                                               │
          │  Demand · Inventory · Supplier · Alt-Sourcing · Impact        │
          │                        │                                      │
          │                        ▼                                      │
          │                  Supervisor (routes · aggregates · resolves)  │
          └───────────────────────────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
   ┌────────────┐              ┌──────────────┐          ┌──────────────────────┐
   │  Decision  │              │  Scenario    │          │ HITL + Simulated     │
   │Intelligence│              │  Simulator   │          │ Action Adapter       │
   └────────────┘              └──────────────┘          └──────────────────────┘
```

### Data flow between layers

| From | To | Payload | Transport |
|---|---|---|---|
| Ingestion | Processing | Validated rows + lineage | SQL (Postgres / SQLite dev) |
| Processing | Predictive ML | Feature frames per product-store | In-process DataFrames |
| Predictive ML | Exception Engine | Forecasts, risk scores, anomaly flags | Function calls + persisted artifacts |
| Exception Engine | Event Bus | `StockoutRiskDetected`, `DemandAnomalyDetected`, … | Outbox → in-proc dispatcher |
| Event Bus | Agent Supervisor | Correlated exception payload | Async consumer |
| Supervisor | Specialist agents | Typed `AgentState` slice | Pydantic in/out |
| Each agent | ThreatGuard (preflight) | System prompt + user payload | In-process call (soft / strict) |
| ThreatGuard | AgentState | `ThreatFinding` list (code · severity · message · detail) | Appended to `security_findings` |
| Agents | Decision layer | Validated evidence (post-sanitize rationale) | Structured JSON returns |
| Decision layer | API | `Recommendation` records | REST `/api/v1` |
| API | Frontend | Dashboards, approval queue | HTTPS JSON |
| Approval | Action Adapter | Signed decision | Simulated executor |

Full diagrammed version: [`architecture.html`](architecture.html).

---

## Agent workflow

The Supervisor fans out to the subset of specialists the exception category requires. Each specialist is wrapped by a `ThreatGuard` that runs OWASP Top 7 pre- and post-flight checks. Max-step, retry and timeout are enforced per node.

### Six specialists

| Agent | Responsibility | Allowed tools |
|---|---|---|
| **Demand Intelligence** | Spike / drop classification, promotion & season decomposition, forecast-vs-actual deltas. | `forecast_demand` |
| **Inventory Intelligence** | Days-of-supply, excess / aging, cross-store imbalance. | `stockout_probability`, `find_transfer_candidates` |
| **Supplier Risk** | OTD, lead-time variance, affected open POs. | `supplier_reliability`, `find_alt_suppliers` |
| **Alternative Sourcing** | Eligibility, capacity, lead-time and cost comparison. | `find_alt_suppliers` |
| **Business Impact** | Revenue-at-risk vs intervention cost, net benefit, assumptions. | `lookup_product` |
| **Decision Orchestrator / Supervisor** | Routes, aggregates evidence, applies deterministic priority rules. | (control-plane only) |

Each specialist returns a **Pydantic-validated evidence object**. The supervisor aggregates, resolves conflicts with deterministic priority rules (LLM arbitration only on ties), and emits a ranked list of **schema-complete** recommendations.

---

## Security — OWASP Top 7 for LLMs

A defensive layer wired into every specialist agent. Implemented in `app/security/threat_model.py`, invoked by each agent in `app/agents/specialists.py`. Findings are attached to `AgentState.security_findings` and the per-step trace.

### Guard pipeline per agent

```
Preflight → Tool-call guard → LLM call → Sanitize output → Record findings
   │              │              │             │                  │
 LLM01/02/04   LLM03/06     Agent core    LLM02/05/07         AgentState audit
```

### The seven controls

| OWASP | Threat | What the guard does | Where it fires |
|---|---|---|---|
| `LLM01` | Prompt Injection | Pattern-scans every string in system+user payload and untrusted evidence; directives are ignored and the attempt logged. | `ThreatGuard.preflight()` |
| `LLM02` | Sensitive Information Disclosure | Redacts secrets (API keys, tokens, passwords) and PII (SSN, cards, email, phone) on both inbound and outbound paths. | `preflight()` + `sanitize_output()` |
| `LLM03` | Supply Chain | Pins LLM provider and model against `APPROVED_PROVIDERS`; refuses any tool call outside `ALLOWED_TOOL_ARGS`. | `_check_supply_chain()` + `guard_tool_call()` |
| `LLM04` | Data & Model Poisoning | Replaces NaN/Inf with 0, clamps probabilities to [0,1], drops negatives for non-negative fields, caps magnitudes at 10¹². | `_bound_check_evidence()` |
| `LLM05` | Improper Output Handling | Validates the LLM reply is a JSON object with expected keys; truncates oversized output; drops unexpected tool arguments. | `_run_llm()` + `guard_tool_call()` |
| `LLM06` | Excessive Agency | Enforces per-agent `AGENT_TOOL_SCOPE`; cross-agent tool call blocked. Flags critical-tier state bypassing the approval gate. | `guard_tool_call()` + `_check_excessive_agency()` |
| `LLM07` | System Prompt Leakage | Scrubs rationale for echoes of the system prompt and verbatim leakage of first 32 bytes. | `sanitize_output()` |

**Modes.** *Soft (default)*: record `ThreatFinding` with severity `info · warn · high` and continue with a sanitized payload. *Strict (production)*: any `high`-severity finding raises `ThreatViolation` and the agent step is marked `blocked by threat guard`.

### Transport & platform security

JWT auth + five roles (`analyst`, `store_mgr`, `procurement`, `director`, `admin`); role-based authority tiered to risk; rate limits; Pydantic validation on every input; parameterised SQL only; CORS allowlist; prompt-injection detector + untrusted-text normalisation; 25 MB upload cap; secret redaction in prompts and logs; audit trail on every approval.

---

## Engineering decisions (ADRs)

Each decision names the alternative rejected, the why, and the trade-off accepted.

| Decision | Rejected alternative | Why | Trade-off accepted |
|---|---|---|---|
| **Typed-state orchestrator in pure Python** | `langgraph` + LangChain dependency chain | Three features I actually need (typed state, conditional edges, approval interrupt) in ~200 lines with full determinism and no framework version risk. | No built-in checkpoint persistence or streaming; a future port to `langgraph` is mechanical. [ADR 0001](docs/decisions/0001-orchestrator-in-pure-python.md) |
| **Deterministic math; LLM only explains** | Let the LLM propose numeric fields | A retail controller cannot approve a $-figure invented by an LLM. | Less conversational drill-down; a dedicated QA endpoint can be added later. [ADR 0002](docs/decisions/0002-deterministic-math-llm-reasoning.md) |
| **Four separate predictive models** | One unified multi-task model | Each task has its own metric family and baseline, so upgrades are honest. | More modules; clarity and auditability win. [ADR 0003](docs/decisions/0003-separate-predictive-models.md) |
| **Postgres outbox + in-proc broker** | Local Kafka / Kinesis | Single DB transaction for state + outbox row; idempotent consumers; clean SNS → SQS port. | Single-node throughput ceiling; triggers for a distributed broker documented. [ADR 0004](docs/decisions/0004-events-outbox.md) |
| **Python / FastAPI as the primary API** | C# / .NET Core parallel stack | ML + agents are Python-native; two API stacks would double surface area. OpenAPI is the contract. | No .NET story in this build; schema is generator-ready. [ADR 0005](docs/decisions/0005-api-stack.md) |
| **Postgres primary, SQLite in dev** | Require Postgres for every local run | Instant local loop for every engineer. | SQLite's lighter FK enforcement — not a correctness issue for dev. [ADR 0006](docs/decisions/0006-postgres.md) |
| **Simulated action adapter** | Auto-execute approved recommendations | Correct safety posture for AI-proposed supply-chain actions. | No real "did it happen" loop; connector is a later isolated integration. |
| **Mock LLM default; Bedrock/OpenAI behind one interface** | Require a paid provider to run the stack | Reproducible, deterministic demos & tests. | Live-provider latency / cost / schema compliance aren't measured by default. |

---

## Technology stack

| Layer | Technology |
|---|---|
| **API** | FastAPI · Pydantic v2 · Uvicorn · OpenAPI 3.1 |
| **ORM / DB** | SQLAlchemy 2 · Alembic · **PostgreSQL 15** (prod) / **SQLite** (dev) |
| **ML** | scikit-learn · XGBoost · pandas · NumPy |
| **Agents** | Custom typed-state orchestrator (LangGraph-equivalent) in pure Python |
| **LLM providers** | Mock (default) · Bedrock · OpenAI-compatible (behind one interface) |
| **Events** | Postgres outbox → in-proc dispatcher → (prod) SNS / SQS / EventBridge |
| **Observability** | Structured JSON logs · OTEL traces · Prometheus `/metrics` |
| **Frontend** | React 18 · Vite · TypeScript · Tailwind CSS · Recharts |
| **Testing** | pytest · pytest-asyncio · Playwright (frontend smoke) |
| **Lint / type** | ruff · mypy |
| **Infra** | Docker Compose (local) · Terraform (AWS reference) |
| **Cloud reference** | ECS Fargate · RDS · ElastiCache · S3 · SQS / SNS / EventBridge · CloudWatch · ALB |

---

## Prerequisites

Install the following before first run:

| Tool | Version | Verify |
|---|---|---|
| **Python** | 3.12.x | `python --version` |
| **Node.js** | 20.x LTS | `node --version` |
| **npm** | ≥ 10 | `npm --version` |
| **Docker Desktop** *(optional)* | ≥ 24 | `docker --version` |
| **Docker Compose** *(optional)* | v2 plugin | `docker compose version` |
| **Git** | 2.x | `git --version` |
| **Make** *(optional)* | Any | `make --version` |

**OS support.** macOS · Linux · Windows 10/11 (PowerShell or WSL2). Ports **5173** (frontend) and **8000** (backend) must be free.

---

## Installation & setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/retail-nexus-ai.git
cd retail-nexus-ai
```

### 2. Choose a run mode

Two supported paths:

- **Path A — Docker Compose** (recommended; zero local tooling after Docker).
- **Path B — Native** (Python venv + Node; runs backend and frontend as separate processes).

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./app.db` | SQLAlchemy URL. Leave unset for SQLite dev loop. |
| `JWT_SECRET` | *(generate)* | HS256 signing key. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `LLM_PROVIDER` | `mock` | One of `mock` · `bedrock` · `openai`. |
| `LLM_MODEL` | `mock-haiku` | Must appear in `APPROVED_PROVIDERS`. |
| `AWS_REGION` | `us-east-1` | Only when `LLM_PROVIDER=bedrock`. |
| `OPENAI_API_KEY` | *(empty)* | Only when `LLM_PROVIDER=openai`. |
| `THREAT_GUARD_MODE` | `soft` | `soft` or `strict`. Strict raises on `high` findings. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list. |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARN` / `ERROR`. |

---

## Running the application

### Path A — Docker Compose (one command)

```bash
docker compose up --build
```

Docker spins up four services: **backend** (FastAPI), **frontend** (Vite dev server), **db** (Postgres), **redis**. On first boot the backend runs migrations, generates the synthetic dataset, and loads it.

Services reachable at:

| Service | URL | Credentials |
|---|---|---|
| **UI** | http://localhost:5173 | `demo-admin / demo` |
| **API** | http://localhost:8000 | — |
| **API docs (Swagger)** | http://localhost:8000/docs | — |
| **API docs (ReDoc)** | http://localhost:8000/redoc | — |
| **Prometheus metrics** | http://localhost:8000/metrics | — |
| **Health probe** | http://localhost:8000/health | — |

Stop the stack with `Ctrl+C`, then `docker compose down`. Add `-v` to also drop the DB volume.

### Path B — Native (no Docker)

#### Backend

```bash
cd backend

# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
#    macOS / Linux
source .venv/bin/activate
#    Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
#    Windows (cmd.exe)
.venv\Scripts\activate.bat

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Generate the synthetic dataset (reproducible seed)
python -m app.data.generate --seed 42

# 6. Load it into the database
python -m app.data.load

# 7. (Optional) Train baseline ML models
python -m app.ml.train_all

# 8. Start the API with hot reload
uvicorn app.main:app --reload --port 8000
```

#### Frontend (new shell)

```bash
cd frontend
npm install
npm run dev
```

Frontend auto-opens at **http://localhost:5173**. Default login: `demo-admin / demo`.

### First-run walkthrough

1. Open the UI at http://localhost:5173 and sign in.
2. Navigate to **Exceptions** — the seeded run produces ~100-200 open exceptions across 11 categories.
3. Click any exception to open its **Investigation** — the agents are invoked synchronously (seconds on mock LLM).
4. Review the ranked **Recommendations** with their evidence, assumptions, revenue-at-risk and net-benefit math.
5. Use **Approve · Reject · Request-more-evidence** to see the HITL loop and audit trail.

### Useful Make targets

```bash
make test          # pytest with coverage
make lint          # ruff
make typecheck     # mypy (soft gate)
make evaluate      # ML + agent evaluation → ml/evaluation/report.json
make generate-data # synthetic dataset → data/synthetic/
make load-data     # ingest into DB
make migrate       # alembic upgrade head
make clean         # remove caches, .pyc, node_modules/.cache
```

---

## Configuration

### Database

- **Default**: SQLite at `./app.db` — zero setup.
- **Production**: set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`. Run `alembic upgrade head`.

### LLM provider

Swap providers by changing one environment variable:

```bash
# Default — deterministic mock, zero cost
LLM_PROVIDER=mock

# AWS Bedrock (Claude 3.5 Haiku recommended)
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-5-haiku-20241022-v1:0
AWS_REGION=us-east-1

# OpenAI-compatible
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

A provider / model not on the `APPROVED_PROVIDERS` list is refused by the `LLM03` guard.

### Threat guard mode

- `soft` — findings are recorded and travel in `security_findings`. The agent still produces evidence (good for dev).
- `strict` — a `high`-severity finding raises `ThreatViolation`, the step is marked `blocked by threat guard`, and no poisoned number reaches the decision layer (production profile).

---

## Testing & evaluation

### Unit & integration tests

```bash
cd backend
pytest -q                          # all tests
pytest tests/security/ -q          # OWASP guard suite
pytest tests/agents/ -q            # agent routing + schema
pytest --cov=app --cov-report=term # with coverage
```

### Frontend smoke

```bash
cd frontend
npm run test        # vitest unit tests
npm run e2e         # Playwright end-to-end
```

### ML & agent evaluation

```bash
make evaluate
# → ml/evaluation/report.json
```

**Predictive models** — each reported alongside its baseline:

| Model | Baseline | Target metric | Release gate |
|---|---|---|---|
| Demand forecast | Seasonal naive (7-day lag) | MAPE ↓ 20 % vs baseline on fast-movers · bias ± 3 % | No regression > 2 pp vs last green |
| Stockout classifier | Days-of-supply < 5 rule | Precision ≥ 0.75 · Recall ≥ 0.70 · ROC-AUC ≥ 0.85 | PR-AUC ≥ baseline + 0.05 |
| Demand anomaly | ± 2 σ z-score | F1 ≥ 0.65 on labelled promo-vs-spike | No new false-positive class above threshold |
| Supplier delay | 1 − OTD historical rate | Brier ≤ 0.12 · calibration ± 5 % | Calibration plot reviewed per release |

**Agent & recommendation quality**:

- Evidence-grounding accuracy ≥ 99 % (every $-figure traceable to `EvidenceEntry.data`).
- Schema compliance 100 % (Pydantic at agent boundary; zero `LLM05 · high` in a release window).
- Hallucination rate < 1 % (LLM-as-judge + 1 % manual spot-check).
- LLM cost / decision P95 ≤ $0.025.

Methodology: [`docs/evaluation/methodology.md`](docs/evaluation/methodology.md).

### Release gates

- **Offline eval** — golden dataset + metric suite required green on every PR.
- **Shadow mode** — new model runs alongside production for ≥ 7 days; outputs logged but not acted on.
- **Canary rollout** — 5 % → 25 % → 100 % traffic over 48 h. Auto-rollback on SLO burn or finding-severity spike.
- **Model registry** — every version immutable, signed, tied to training commit hash + dataset hash. Rollback is a pointer change.

---

## Repository layout

```
.
├── backend/                 FastAPI, agents, ML, services, repositories
│   ├── app/
│   │   ├── agents/          Specialist + supervisor agents, threat guard
│   │   ├── api/             REST endpoints (/api/v1)
│   │   ├── data/            Synthetic generator, loader, schemas
│   │   ├── decision/        Recommendation + what-if simulator
│   │   ├── events/          Outbox + dispatcher
│   │   ├── exception/       11-category exception engine + risk scoring
│   │   ├── ml/              Predictive models + evaluation harness
│   │   ├── repositories/    Data access layer
│   │   ├── security/        ThreatGuard, OWASP Top 7 implementation
│   │   ├── services/        Business logic
│   │   └── main.py
│   ├── tests/               pytest (unit, integration, security, agents, eval)
│   └── requirements.txt
├── frontend/                React + Vite + Tailwind + Recharts
│   ├── src/                 Pages, components, hooks, api client
│   └── package.json
├── data/                    Synthetic dataset & schemas
├── ml/                      Trained artifacts, evaluation reports
├── docs/
│   ├── decisions/           ADRs 0001–0006
│   ├── evaluation/          methodology.md
│   └── security/            Threat model, test matrix
├── infrastructure/
│   ├── docker/              Dockerfiles
│   ├── terraform/           AWS reference (skeletons)
│   └── aws/                 Topology README
├── scripts/                 Operational scripts
├── architecture.html        Full diagrammed architecture
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

---

## Scale & cost model

### Target scale (one Tier-1 retailer)

| Dimension | Value |
|---|---|
| Suppliers | 10,000 |
| Stores (retail + DC) | 5,000 |
| Customers / day | 100,000 |
| SKUs | 500,000 |
| Active product-store pairs | 50 M (sparse of 2.5 B grid) |
| POS line items / day | 500,000 |
| Open POs / day | 7,000 |
| Exceptions detected / day | 100,000 |

### Agent workload

| Triage tier | Exceptions / day | Agent fan-out | Agent invocations / day | LLM used |
|---|---:|---|---:|:---:|
| Critical / High | 20,000 | Full 5-agent | 100,000 | yes |
| Medium | 50,000 | Partial (2 agents avg) | 100,000 | yes |
| Low / Info | 30,000 | Supervisor rules path | 0 | no |
| **Total LLM-backed** |  |  | **200,000 / day** |  |

### Annual run cost (year 1)

Primary model **Claude 3.5 Haiku** via Bedrock (~1,500 in + 500 out tokens/call, +20 % headroom).

| Category | Monthly | Annual | Notes |
|---|---:|---:|---|
| AI tokens (Haiku, 20 % headroom) | $23,040 | $280,320 | 73 M LLM calls / yr |
| Mixed-model routing (Sonnet on critical) | $10,000 | $120,000 | Optional, per-tenant toggle |
| AWS infrastructure (multi-AZ on-demand) | $16,230 | $194,760 | ECS · RDS · ElastiCache · S3 · SageMaker · OTEL |
| Third-party SaaS | $5,417 | $65,000 | Datadog · PagerDuty · Snyk · SonarCloud · Langfuse |
| **Run cost (excl. labour)** | **$54,687** | **~ $660,080** |  |

### Unit economics

| Metric | Value | Derivation |
|---|---:|---|
| Cost per exception investigated | **$0.018** | $660 K ÷ 36.5 M exceptions / yr |
| Defensible SaaS price per exception | $0.05 – 0.10 | 3-5 × markup, below lost margin |
| Avg value of one avoided stockout | $3 – 6 | Industry benchmark on lost margin |
| Break-even conversion rate | ~ 0.4 % | 1 in 250 recommendations |
| Gross margin on AI workload | 60-80 % | Price vs cost, pre-infra allocation |

### Cost levers

| Lever | Direction | Impact |
|---|:---:|---|
| 1-yr RI + 3-yr savings plan on AWS | ↓ | ~ $55 K / yr |
| 70 % prompt-cache hit on system prompt + tool schema | ↓ | ~ $55 K / yr |
| Route 10 % more low-tier exceptions to rules-only | ↓ | ~ $28 K / yr |
| Full Sonnet escalation on critical tier | ↑ | ~ $120 K / yr |
| Multi-region active-active DR | ↑ | ~ $80 K / yr |

### Capacity targets (planned load test)

| Metric | Target | Status |
|---|---|---|
| Events processed / sec | ≥ 1,200 ev/s | Planned (k6 soak) |
| Concurrent agent executions | ≥ 400 in-flight | Planned |
| P50 recommendation latency | ≤ 2.5 s | Planned |
| P95 recommendation latency | ≤ 8 s | Planned |
| P99 recommendation latency | ≤ 20 s | Planned |
| Queue backlog recovery (100 k burst) | ≤ 10 min | Planned |
| DB sustained TPS | ≥ 3,500 read / 400 write | Planned (pgbench) |
| Measured cost / recommendation | ≤ $0.025 | Planned |

---

## Business impact & revenue potential

### Lens 1 — value unlocked inside one Tier-1 retailer

| Value lever | Baseline loss at $50 B retailer | Realistic improvement | $ recovered / yr |
|---|---|---|---:|
| Lost sales from stockouts | ~ 3 % of revenue ≈ $1.5 B | 20-30 % reduction | **$300 – 450 M** |
| Excess & aging inventory carry | Inventory on hand ~ $5-8 B | 10-15 % reduction | **$50 – 120 M** |
| Supplier-delay expedites | ~ $150-300 M / yr ad-hoc | 15-20 % fewer | **$25 – 60 M** |
| Perishable markdown & write-off | ~ 1 % of revenue | 10-15 % better forecasting | **$40 – 70 M** |
| Planner productivity | 800-1,200 FTEs | 5× decisions / analyst / day | **$10 – 20 M** |
| **Total addressable** |  |  | **$425 – 720 M / yr** |

**ROI 600-1,000×** against ~ $660 K run cost. **Payback < 1 week** at lower bound.

### Lens 2 — SaaS ARR potential

| Segment | Profile | Target | Price / yr | Year-5 capture | Year-5 ARR |
|---|---|---|---:|---|---:|
| Hyperscale | > 5 k stores · $50 B+ rev | ~ 30 globally | $5-15 M | 3-5 logos | $25-60 M |
| Enterprise | 1-5 k stores · $10-50 B rev | ~ 150 globally | $1.5-3 M | 15-25 logos | $30-60 M |
| Mid-market | 300-1 k stores · $1-10 B rev | ~ 500 globally | $300-700 K | 40-80 logos | $20-40 M |
| **Realistic 5-year ARR** |  |  |  |  | **$75-150 M** |

### Alternative monetisation

- **Per-exception usage** — $0.05-0.10 per investigated exception (3-5× markup on $0.018 cost) → ~ $50 M / yr at 20-tenant scale.
- **Success fee on recovered revenue** — 3-5 % of measured recovery → $12-20 M / logo.
- **Per-decision premium tier** — equivalent to ~ 2 ¢ margin per avoided stockout.
- **Tiered seat + platform license** — classic enterprise pricing.

> **Caveat.** All ranges are modelled from public industry benchmarks applied to the scale assumptions — credible estimates, not quoted contracts. A real engagement re-derives each lever against the operator's own data before any commitment.

---

## Deployment reference (AWS)

### Local dev

Docker Compose: `backend`, `frontend`, `db` (Postgres), `redis`. SQLite fallback for no-Docker laptops.

### AWS production topology

| Component | Service | Sizing |
|---|---|---|
| API backend | ECS Fargate | 10 tasks × 4 vCPU / 8 GB |
| Agent workers | ECS Fargate (autoscale 10-40) | 24 tasks × 4 vCPU / 8 GB |
| Primary DB | RDS Postgres (multi-AZ) | db.r6g.4xlarge + 2 TB gp3 |
| Analytics replica | RDS read replica | db.r6g.2xlarge |
| Cache | ElastiCache Redis | cache.m6g.large × 3 |
| Events | SQS / SNS / EventBridge | ~ 3 M events / day fan-out |
| Artifacts | S3 (+ lifecycle to Glacier) | 4 TB active |
| ML | SageMaker | Weekly retrain, nightly inference |
| Observability | CloudWatch + OTEL collector | 200 GB / day log ingest |
| Edge | ALB + CloudFront + Route 53 | 1 ALB, CDN |
| Security | WAF + Shield + Secrets Manager + KMS | Baseline |

Terraform skeletons in [`infrastructure/terraform/`](infrastructure/terraform/); topology in [`infrastructure/aws/README.md`](infrastructure/aws/README.md).

### Enterprise scale path

- Stateless APIs horizontally scaled behind an ALB.
- Agent runs moved to a worker pool consuming SQS; checkpoints persisted to Postgres (large payloads to S3).
- Read replicas for analytics; CQRS split only if latency demands.
- Feature store can replace in-process feature calc without changing agent code.
- LLM gateway with budget caps and per-tenant provider routing.

---

## Production readiness & reliability

### Service-level objectives

| SLI | SLO target | Measurement |
|---|---|---|
| API availability | 99.9 % monthly | Synthetic probes (30 s) + 5xx-ratio on ALB |
| API latency (reads) | P95 < 300 ms | OTEL spans on `/api/v1/*` |
| Recommendation latency (E2E) | P95 < 8 s · P99 < 20 s | Event-to-recommendation timer |
| Event-processing lag | P95 queue age < 30 s · max < 5 min | SQS `ApproximateAgeOfOldestMessage` |
| Agent success rate | ≥ 99 % per-step | Agent-step status counter |
| Exception-detection freshness | P95 < 15 min source → exception | Timestamp delta |

### Failure modes & recovery

| Failure | Detection | Automatic response |
|---|---|---|
| Agent timeout | Max-step budget exceeded | Step failed, partial evidence recorded, exception stays open |
| LLM 5xx / rate-limit | HTTP error + token-meter spike | Exponential back-off; failover to mock for non-critical tiers |
| Duplicate event delivery | Outbox `event_id` seen | Idempotent consumer; duplicate dropped with metric |
| Queue back-pressure | Queue age > 60 s for > 5 min | Worker autoscale; non-critical events rerouted to delay queue |
| Model-quality dip | Offline eval fails on nightly re-score | Automatic rollback to previous model version |
| DB primary failure | RDS multi-AZ health probe | AZ failover (RTO ≤ 2 min) |
| Region impairment | Pilot light region health checks | DNS failover to warm standby (RTO ≤ 30 min) |

### Disaster recovery & rollback

- **RTO ≤ 30 min · RPO ≤ 5 min** — cross-region warm-standby with continuous RDS PITR + S3 cross-region replication.
- **Agent & prompt versioning** — all in-repo, rollback via config flag (no redeploy).
- **Model version rollback** — pointer swap in registry; previous version warm for 30 days.
- **Schema evolution** — expand-contract migrations with a dual-read period; `/api/v2` ships alongside `/api/v1` with 90-day deprecation.
- **Chaos drills** — monthly game-day (kill worker, choke SQS, inject 5xx on LLM, fail an AZ).
- **Audit & replay** — every decision persisted with feature frame, model version, prompt version, evidence snapshot.

---

## AI governance & operating controls

| Control area | What's in place / designed | Owner |
|---|---|---|
| Model approval & lifecycle | Every version: training commit, dataset hash, offline-eval scorecard, risk-tier, approved-by, rollback version. | AI/ML eng + Governance lead |
| Data lineage & quality | Every feature tagged with source table, DQ rules, owner, PII class. Lineage graph queryable per recommendation. | Data engineering |
| RBAC & tenant isolation | 5-role RBAC; multi-tenant: row-level security on Postgres, per-tenant S3 prefix + KMS key, per-tenant SQS. | SRE & Security |
| Auditability & compliance | Every recommendation + approval persisted with evidence, approver, timestamp, OWASP findings. 7-yr retention. SOC 2 Type II scoped. | Security + Legal |
| Human override & escalation | Approver can reject, request-more-evidence, or override action type. Overrides counted, reviewed weekly, feed eval harness. | Platform + AI/ML eng |
| Model & data drift | PSI / KL on top features; prediction-distribution drift; concept-drift from approval-rate dips. | AI/ML eng |
| Incident response | Sev-1 / Sev-2 include "wrong recommendation acted on". Blameless postmortems within 5 business days. | SRE + Governance |
| Prompt & agent-config change mgmt | Prompts, tool scopes, OWASP config are code. PRs reviewed by AI/ML + Security. Change log carries eval-delta. | AI/ML eng + Security |
| Third-party / supply-chain risk | LLM provider pinned (`LLM03`); Snyk dependency scan; signed container images; vendor SOC 2 collected. | Security |

---

## Phased transformation roadmap

| Phase | Window | Scope | Gate | Measure |
|---|---|---|---|---|
| **1. Data foundation** | 0-3 mo | Land source feeds; feature store; lineage; read-only exception dashboard. | 95 % DQ pass on top 10 features; lineage queryable E2E. | Detection latency ≤ 1 h. |
| **2. Predictive intelligence** | 3-6 mo | Ship 4 predictive models + eval harness. Shadow mode → operator-visible scores. | All 4 models beat baseline on release gate. | Stockout recall ≥ 0.70 on labelled history. |
| **3. Agent-assisted decisions** | 6-12 mo | Specialist agents + OWASP guard live; approval queue live; action adapter simulated. | Recommendation acceptance ≥ 60 % on Medium tier. | Stockout rate ↓ 10 % vs baseline in pilot stores. |
| **4. Governed enterprise integrations** | 12-18 mo | Real ERP / WMS / supplier EDI via hardened adapter. Multi-tenant isolation hardened. SOC 2 in progress. | Tenant isolation + attestation evidence complete. | $425 M lower bound validated in-flight. |
| **5. Multi-region scale** | 18-30 mo | Active-active across 2 regions; continuous retraining; outcome-based SaaS pricing; chaos drills quarterly. | DR drill passes RTO/RPO 2 consecutive quarters. | 99.9 % availability rolling 90 days. |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `uvicorn: command not found` | venv not activated | Activate: `source .venv/bin/activate` (or Windows equivalent). |
| `psycopg.OperationalError: connection refused` | Postgres not running | Start DB (`docker compose up db -d`) or fall back to SQLite by unsetting `DATABASE_URL`. |
| `alembic.util.CommandError: Can't locate revision` | Mixed branches on migrations | `alembic downgrade base && alembic upgrade head`. |
| `npm ERR! EACCES` on install | Permission on `node_modules` | Delete `frontend/node_modules`, re-run `npm install`. |
| Port 8000 or 5173 in use | Another process | Change port: `uvicorn app.main:app --port 8001` / `vite --port 5174`. |
| `LLM03 · high` finding on startup | Unapproved provider / model | Set `LLM_PROVIDER=mock`, or add the pair to `APPROVED_PROVIDERS`. |
| `ThreatViolation: blocked by threat guard` | Strict mode + legitimate high finding | Review `security_findings`; fix root cause or switch `THREAT_GUARD_MODE=soft` for dev. |
| Agents produce empty recommendations | Dataset not loaded | Run `python -m app.data.generate --seed 42 && python -m app.data.load`. |
| Frontend shows 401 on every call | Expired JWT | Log out and back in; check `JWT_SECRET` is stable. |
| `make: command not found` on Windows | No Make installed | Run the raw commands in the Makefile directly, or use WSL2. |

Open an issue with the request id (`X-Request-Id` header, visible in every API response) and the backend log line — logs are JSON and tagged with correlation ids.

---

## Known limitations

- **Benchmarks are against synthetic data** generated with fixed seeds. Numbers are reproducible as a methodology demonstration, not evidence of real-world accuracy.
- **The .NET REST API** mentioned in the original spec is **not** built; the primary API is Python/FastAPI (see [ADR 0005](docs/decisions/0005-api-stack.md)).
- **LLM mode defaults to a deterministic mock.** External providers (Bedrock, OpenAI-compatible) are wired behind an abstraction but not credentialled in this repo.
- **Simulated action adapter** — the "execute" step is a no-op that emits an event. No connector to a real ERP/WMS — correct safety posture for this build.
- **Multi-tenant isolation** at the physical layer is planned but not built.
- **Continuous retraining pipelines** are planned but not built.
- **Not production-deployed.** Terraform definitions are reference only.

---

## Contributing

1. Fork and branch from `main`.
2. Create a feature branch: `git checkout -b feat/<short-slug>`.
3. Install dev deps: `pip install -r backend/requirements-dev.txt` and `cd frontend && npm install`.
4. Install pre-commit hooks: `pre-commit install`.
5. Run `make lint typecheck test` locally before pushing.
6. Open a PR; CI must be green before review.

For architectural changes, add an **ADR** in `docs/decisions/` with the alternatives rejected, the why, and the trade-off accepted. ADRs are reviewed in the bi-weekly architecture sync.

---

## License

MIT — see [`LICENSE`](LICENSE).

---

## Author

**Pradeep Sahoo** — Engineering Lead. Architect of record for **Retail Nexus AI**.

I designed and built this platform end-to-end across predictive ML, agentic orchestration, decision intelligence, event-driven backbone, enterprise security, observability and the operator dashboard. I am the engineer of record for every architectural call in this README and in [`docs/decisions/`](docs/decisions/), accountable for scope, architecture, build quality, and the trade-offs documented above.

**Signed authority on:** scope & architecture · predictive ML methodology · multi-agent workflow & safety · event-driven backbone · security & HITL governance · cloud/AWS reference topology · observability.

> See the full diagrammed architecture at [`architecture.html`](architecture.html).

---

*© 2026 **Pradeep Sahoo** — Engineering Lead. Architect of record for **Retail Nexus AI**.*
