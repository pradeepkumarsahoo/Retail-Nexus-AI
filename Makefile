# Author: Pradeep Sahoo — Retail Nexus AI
.PHONY: install test lint typecheck evaluate generate-data load-data run-backend run-frontend compose-up compose-down

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app tests

typecheck:
	cd backend && mypy app

evaluate:
	cd backend && python -m app.ml.evaluate

generate-data:
	cd backend && python -m app.data.generate --seed 42

load-data:
	cd backend && python -m app.data.load

run-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v
