# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report suspected vulnerabilities privately by emailing the maintainer at
`pradeepsahoo.ms@gmail.com` with the subject `[SECURITY] Retail Nexus AI`.

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce (minimal proof of concept preferred).
- Affected component (backend, frontend, agent, data pipeline, infra).
- Your name and affiliation (optional, for acknowledgement).

You will receive an acknowledgement within **72 hours** and a triage
response within **7 days**. Fixes for confirmed high/critical issues target
a **14-day** disclosure window, coordinated with the reporter.

## Scope

In scope:

- Code in this repository (`backend/`, `frontend/`, `ml/`, `infrastructure/`).
- Container images built from the `Dockerfile`s in this repository.
- Documented APIs under `/api/v1/*`.

Out of scope:

- Issues affecting only the synthetic dataset or local-only `mock` LLM provider.
- Denial-of-service findings against unauthenticated development endpoints.
- Findings that require the attacker to already have root on the host.

## Security considerations for operators

Retail Nexus AI integrates LLM agents with operational data. Before deploying:

1. Review the threat model at [`docs/security/threat-model.md`](docs/security/threat-model.md).
2. Confirm the OWASP Top 7 for LLMs guards are enabled (see README § Security).
3. Rotate `APP_SECRET_KEY` and all LLM provider credentials.
4. Restrict `CORS_ALLOWED_ORIGINS` to known front-ends.
5. Run the simulated-action adapter in dry-run mode before enabling real
   ERP / OMS writes; every mutating action must pass human approval.

## Dependency hygiene

- Backend dependencies are pinned in `backend/requirements.txt` and scanned
  by Dependabot weekly.
- Frontend dependencies are pinned in `frontend/package-lock.json` and
  scanned by Dependabot weekly.
- CI runs `pip-audit` on every pull request; failing findings block merge
  unless an exception is documented in `docs/security/`.
