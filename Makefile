# Author: Pradeep Sahoo — Retail Nexus AI
SHELL := /bin/bash
.DEFAULT_GOAL := help

PY       ?= python
PIP      ?= pip
BACKEND  := backend
FRONTEND := frontend

.PHONY: help install install-backend install-frontend install-dev \
        lint lint-backend lint-frontend format format-check \
        typecheck typecheck-backend typecheck-frontend \
        test test-backend test-frontend coverage \
        audit audit-backend audit-frontend \
        precommit evaluate generate-data load-data \
        run-backend run-frontend compose-up compose-down compose-logs \
        docker-build docker-build-backend docker-build-frontend clean

## help: show this help
help:
	@echo "Retail Nexus AI — developer commands"
	@echo
	@grep -E '^##' Makefile | sed -E 's/^## /  /'
	@echo

## install: install backend + frontend runtime deps
install: install-backend install-frontend

install-backend:
	cd $(BACKEND) && $(PIP) install -r requirements.txt

install-frontend:
	cd $(FRONTEND) && npm ci || (cd $(FRONTEND) && npm install)

## install-dev: install backend dev deps + pre-commit hooks
install-dev:
	cd $(BACKEND) && $(PIP) install -r requirements-dev.txt
	cd $(FRONTEND) && (npm ci || npm install)
	pre-commit install --install-hooks

## lint: ruff + eslint
lint: lint-backend lint-frontend

lint-backend:
	cd $(BACKEND) && ruff check app tests

lint-frontend:
	cd $(FRONTEND) && npm run lint

## format: autoformat backend + frontend
format:
	cd $(BACKEND) && ruff format app tests
	cd $(FRONTEND) && npm run format

## format-check: check formatting without writing
format-check:
	cd $(BACKEND) && ruff format --check app tests
	cd $(FRONTEND) && npm run format:check

## typecheck: mypy + tsc
typecheck: typecheck-backend typecheck-frontend

typecheck-backend:
	cd $(BACKEND) && mypy app

typecheck-frontend:
	cd $(FRONTEND) && npm run typecheck

## test: backend + frontend tests
test: test-backend test-frontend

test-backend:
	cd $(BACKEND) && pytest

test-frontend:
	cd $(FRONTEND) && npm test -- --run

## coverage: backend coverage report
coverage:
	cd $(BACKEND) && pytest --cov=app --cov-report=term --cov-report=html --cov-report=xml

## audit: pip-audit + npm audit
audit: audit-backend audit-frontend

audit-backend:
	cd $(BACKEND) && pip-audit -r requirements.txt

audit-frontend:
	cd $(FRONTEND) && npm audit --audit-level=high || true

## precommit: run all pre-commit hooks on all files
precommit:
	pre-commit run --all-files

## evaluate: run model evaluation
evaluate:
	cd $(BACKEND) && $(PY) -m app.ml.evaluate

## generate-data: regenerate the synthetic dataset
generate-data:
	cd $(BACKEND) && $(PY) -m app.data.generate --seed 42

## load-data: load the synthetic dataset into the database
load-data:
	cd $(BACKEND) && $(PY) -m app.data.load

## run-backend: run the API locally with reload
run-backend:
	cd $(BACKEND) && uvicorn app.main:app --reload --port 8000

## run-frontend: run the Vite dev server
run-frontend:
	cd $(FRONTEND) && npm run dev

## compose-up: start the full stack via docker compose
compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

compose-logs:
	docker compose logs -f --tail=200

## docker-build: build backend + frontend images
docker-build: docker-build-backend docker-build-frontend

docker-build-backend:
	docker build -t retail-nexus-ai/backend:local ./$(BACKEND)

docker-build-frontend:
	docker build --target runtime -t retail-nexus-ai/frontend:local ./$(FRONTEND)

## clean: remove local build + cache artifacts
clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
	rm -rf $(BACKEND)/htmlcov $(BACKEND)/.coverage $(BACKEND)/coverage.xml
	rm -rf $(FRONTEND)/dist $(FRONTEND)/coverage
