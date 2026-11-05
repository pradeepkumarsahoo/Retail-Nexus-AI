# Contributing to Retail Nexus AI

Thanks for your interest in improving the project. This guide covers how to set
up a development environment, the quality gates we enforce, and the house rules
that keep the codebase trustworthy.

## Code of conduct

This project adopts the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating you agree to uphold it.

## Security issues

Do **not** open public issues for vulnerabilities — see [SECURITY.md](SECURITY.md).

## Prerequisites

- Python **3.12** (Linux / macOS / WSL recommended)
- Node **≥ 20** and npm **≥ 10**
- Docker ≥ 24 and docker compose (optional, for the full stack)
- GNU make

## Local setup

```bash
# one-time: install everything incl. dev deps + git hooks
make install-dev

# generate + load the synthetic dataset
make generate-data load-data

# run the API with auto-reload on :8000
make run-backend

# in another shell, run the Vite dev server on :5173
make run-frontend
```

Or bring the full stack up with:

```bash
make compose-up
```

## Quality gates

Every pull request must pass the same checks CI runs. Run them locally first:

| Command            | What it does                                             |
| ------------------ | -------------------------------------------------------- |
| `make lint`        | `ruff check` (backend) + `eslint` (frontend)             |
| `make format`      | `ruff format` + `prettier --write`                       |
| `make format-check`| Fails if formatting is off                               |
| `make typecheck`   | `mypy` (backend) + `tsc --noEmit` (frontend)             |
| `make test`        | `pytest` (backend) + `vitest run` (frontend)             |
| `make coverage`    | Backend coverage report; CI gates on **≥ 80 %** lines    |
| `make audit`       | `pip-audit` + `npm audit --audit-level=high`             |
| `make precommit`   | Runs every pre-commit hook on every file                 |

Pre-commit hooks are installed by `make install-dev`. If you skipped that:

```bash
pip install pre-commit
pre-commit install --install-hooks
```

## Git workflow

1. Branch from `main`: `git checkout -b feat/<short-name>` or `fix/<short-name>`.
2. Make focused commits with messages in the imperative mood
   (`Add supplier-risk anomaly guard`, not `Added guards`).
3. Update `CHANGELOG.md` under `## [Unreleased]` for any user-visible change.
4. Open a pull request against `main`; the template will prompt you for the
   information reviewers need.
5. Expect a review turnaround of ≤ 2 business days.

### Commit message convention

We use lightweight [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <summary>

<optional body>

<optional footer>
```

Common types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`,
`build`, `ci`.

## House rules

- **Every number shown in the UI must come from the backend.** No mocked
  numbers in components.
- **Agents may not invent numeric fields.** Deterministic engines produce
  numbers; the LLM only explains them.
- **Recommendations must be schema-complete.** Missing fields are a bug.
- **No TODO stubs in main code paths.** If a feature is incomplete, document
  it under "Known limitations" in `README.md`.
- **No secrets in git.** `gitleaks` runs in pre-commit and CI; if it finds
  one, rotate the credential immediately.

## Reporting bugs / requesting features

Use the issue templates in `.github/ISSUE_TEMPLATE/` — they ask for the
information the triage process actually needs.

---

*Author: **Pradeep Sahoo**.*
