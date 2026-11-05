# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `LICENSE` (MIT) covering the entire repository.
- `SECURITY.md` with responsible-disclosure policy and scope.
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
- `.editorconfig` for consistent editor settings.
- GitHub Actions workflows for backend (lint + typecheck + tests + coverage),
  frontend (lint + build + tests), and CodeQL static analysis.
- Dependabot configuration for pip, npm, GitHub Actions, and Docker.
- Pull request and issue templates under `.github/`.
- `.pre-commit-config.yaml` wiring ruff, mypy, and basic file hygiene hooks.
- Split `requirements-dev.txt` for dev-only Python dependencies.
- `pytest-cov` configuration with an 80 % line-coverage floor on `backend/app`.
- `.dockerignore` for both backend and frontend contexts.
- Multi-stage, non-root backend and frontend Docker images with healthchecks.
- Frontend ESLint, Prettier, and Vitest configuration with an `npm test` script.
- Makefile targets for `format`, `coverage`, `precommit`, `audit`.
- CI / coverage badges and governance links in the README.

## [0.1.0] - 2026-11-04

### Added

- Initial reference build of Retail Nexus AI.
- FastAPI backend with agents, predictive models, outbox, and HITL approvals.
- React + Vite + TypeScript frontend.
- Synthetic dataset generator and loader.
- Architecture docs, ADRs, threat model, and evaluation methodology.

[Unreleased]: https://github.com/pradeepsahoo-ms/retail-nexus-ai/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pradeepsahoo-ms/retail-nexus-ai/releases/tag/v0.1.0
