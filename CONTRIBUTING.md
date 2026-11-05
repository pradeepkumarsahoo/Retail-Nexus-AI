# Contributing

## Dev loop
```bash
cd backend && pip install -r requirements.txt
python -m app.data.generate --seed 42
python -m app.data.load
uvicorn app.main:app --reload --port 8000

# in another shell
cd frontend && npm install && npm run dev
```

## Quality gates
- `make lint` — ruff
- `make typecheck` — mypy (soft gate)
- `make test` — pytest
- `make evaluate` — ML + agent eval

## Rules
- **Every number shown in the UI must come from the backend.** No mocked numbers in
  components.
- **Agents may not invent numeric fields.** Deterministic engines produce numbers; the
  LLM only explains them.
- **Recommendations must be schema-complete** — missing fields are a bug.
- **No TODO stubs in main code paths.** If the feature isn't done, document it in
  `README.md` under "Known limitations".

---
*Author: **Pradeep Sahoo**.*
