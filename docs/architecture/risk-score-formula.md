# Risk score formula

Exception risk is computed by a transparent weighted sum. Weights are configurable in
`app/services/exceptions_engine.py::RISK_WEIGHTS`.

```
risk_score = clamp01(
    0.35 * severity_signal        # category-specific signal, e.g. stockout probability
  + 0.25 * recency                # 1.0 for today, linearly down to 0 over 30 days
  + 0.20 * coverage               # 0..1 based on data sufficiency (series length / 90)
  + 0.15 * financial              # revenue_at_risk / 10,000 USD, clipped
  + 0.05 * cross_signal_bonus     # +0.3 if a correlated supplier signal exists
)
```

Severity bands:
- `>= 0.75` → CRITICAL
- `>= 0.50` → HIGH
- `>= 0.25` → MEDIUM
- else      → LOW

Each exception's `evidence.risk_score_components` carries the four normalised inputs so
the UI can display the per-feature contribution.

### Rationale
- Weights sum to 1.0.
- No weight is >50%, so no single signal can produce a CRITICAL by itself without any
  evidence of impact or recency.
- A cross-signal bonus (bounded at 0.05) rewards corroborating independent evidence
  (e.g., stockout risk **and** supplier OTD slipping).

---
*Author: **Pradeep Sahoo**.*
