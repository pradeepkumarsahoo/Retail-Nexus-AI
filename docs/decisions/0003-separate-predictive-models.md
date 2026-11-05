# ADR 0003 — Separate predictive models per task

**Status:** Accepted · 2026-11-03

## Context
Four prediction problems live in this platform:
1. Demand forecasting (regression over time series).
2. Stockout risk (classification with calibration requirement).
3. Demand anomaly detection (point-in-time, labelled under synthetic ground truth).
4. Supplier delay (classification at PO level).

## Decision
Keep each as a separate module with its own features, metrics, and baseline.

- `ml/forecasting/`: seasonal naive + EMA baselines, GBM upgrade.
  Metrics: MAE, RMSE, WAPE, sMAPE. Temporal hold-out.
- `ml/stockout/`: deterministic baseline (days-of-supply logistic) + logistic regression.
  Metrics: ROC-AUC, PR-AUC, Brier.
- `ml/anomaly/`: rolling z-score with IsolationForest backup.
  Metrics: precision/recall vs labelled synthetic spike/decline events.
- `ml/supplier/`: deterministic weighted-sum score + logistic regression evaluation.
  Metrics: ROC-AUC, PR-AUC, Brier on held-out POs.

## Consequences
**+** Every model's performance is measured against an honest baseline.  
**+** We can report metrics appropriate to each task.  
**−** More code than a unified "predict anything" model; worth it for clarity.

---
*Author: **Pradeep Sahoo**.*
