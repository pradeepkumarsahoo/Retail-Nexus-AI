# Threat model summary

## Trust boundaries
1. **Browser ↔ FastAPI** — HTTPS in production; JWT bearer tokens; role-based route guards.
2. **API ↔ Database** — least-privilege DB user in deployment (unused locally); parameterised queries only (SQLAlchemy).
3. **API ↔ LLM provider** — The mock provider never leaves the process. Bedrock/OpenAI calls go over TLS with keys sourced from env vars.
4. **External text ↔ LLM prompt** — All retrieved text and user free-text passes through `strip_untrusted()` which flattens directive strings and redacts obvious secrets. Prompt-injection patterns refuse the call.
5. **Agent ↔ ERP** — Does not exist. Execution is a simulated adapter emitting `ActionExecuted`.

## Controls (shipped)
| Control | Where |
|---|---|
| JWT auth + role dependency | `app/security/auth.py` |
| Role-based authority over risk tiers | `can_approve()` + `/approve` endpoint |
| Rate limits (per IP + path) | `app/security/rate_limit.py` |
| Prompt-injection detection | `app/security/sanitize.py` |
| Tool allow-list + arg validation | `app/security/sanitize.validate_tool_call` |
| Input validation | Pydantic everywhere |
| Upload size cap | 25 MB per CSV |
| Secret redaction in logs/prompts | `redact_sensitive()` |
| CORS allowlist | config |
| Audit trail | `approval_events` table, every approval persisted with approver and timestamp |

## Known limitations
- Dev user store is in-memory. For production: swap `_DEV_USERS` for a DB-backed source
  and put bcrypt behind a password-reset flow.
- No CSRF — JWT bearer tokens are used; no cookie auth.
- HTTPS termination is expected to happen at the ingress (ALB / nginx).
- The rate limiter is in-memory and therefore per-node only; for multi-node, back it
  with Redis.

---
*Author: **Pradeep Sahoo**.*
