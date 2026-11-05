# Author: Pradeep Sahoo — Retail Nexus AI
"""Reproducible evaluation pipeline.

Reads from the loaded DB (or the CSV dataset directly) and produces
`ml/evaluation/report.json` with:
- Forecasting metrics for a sample of product-store pairs (baselines vs GBM).
- Stockout classifier metrics (baseline DoS vs logistic regression).
- Supplier delay classifier metrics (baseline 1-OTD vs logistic regression).
- Anomaly detector precision/recall on synthetic labelled events.

The report explicitly distinguishes measured vs synthetic vs illustrative.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.ml.anomaly.detector import evaluate_precision_recall
from app.ml.features import product_store_daily
from app.ml.forecasting.forecast import evaluate_series
from app.ml.stockout.model import build_training_frame
from app.ml.stockout.model import evaluate_models as stockout_eval
from app.ml.supplier.risk import evaluate as supplier_eval


def _data_dir() -> Path:
    here = Path(__file__).resolve().parent
    return (here.parent.parent.parent / "data" / "synthetic").resolve()


def _load() -> dict[str, pd.DataFrame]:
    d = _data_dir()
    frames = {}
    for name in (
        "sales",
        "inventory",
        "purchase_orders",
        "products",
        "stores",
        "suppliers",
        "supplier_products",
        "labels_ground_truth",
    ):
        p = d / f"{name}.csv"
        if p.exists():
            frames[name] = pd.read_csv(p)
    return frames


def _sample_pairs(sales: pd.DataFrame, k: int = 20, seed: int = 42) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    pairs = (
        sales.groupby(["product_id", "store_id"])
        .size()
        .reset_index()
        .rename(columns={0: "n"})
        .sort_values("n", ascending=False)
        .head(100)
    )
    chosen = rng.sample(list(pairs.itertuples(index=False)), k=min(k, len(pairs)))
    return [(r.product_id, r.store_id) for r in chosen]


def run_evaluation(out_path: Path | None = None) -> dict[str, Any]:
    frames = _load()
    report: dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "data_source": "synthetic",
        "notes": "All numbers computed on the shipped synthetic dataset; see data/synthetic/_meta.json.",
    }
    if "sales" not in frames:
        report["skipped"] = "no synthetic data loaded"
        return report

    # Forecasting
    sales = frames["sales"]
    pairs = _sample_pairs(sales, k=15)
    per_pair = []
    agg = {m: {k: [] for k in ("MAE", "RMSE", "WAPE", "sMAPE")} for m in ("seasonal_naive", "ema", "gbm")}
    for pid, sid in pairs:
        hist = product_store_daily(sales, pid, sid)
        if hist.empty:
            continue
        res = evaluate_series(hist, horizon_days=14)
        if "skipped" in res:
            continue
        per_pair.append({"product_id": pid, "store_id": sid, **res})
        for m, metrics in res.items():
            for k, v in metrics.items():
                agg[m][k].append(v)
    forecast_summary = {
        m: {k: round(float(np.mean(v)), 4) if v else None for k, v in metrics.items()}
        for m, metrics in agg.items()
    }
    report["forecasting"] = {
        "method": "temporal_split_last_14_days",
        "samples_evaluated": len(per_pair),
        "aggregate": forecast_summary,
        "per_series_sample": per_pair[:5],  # first 5 for readability
    }

    # Stockout classifier
    if "inventory" in frames and "purchase_orders" in frames:
        tr = build_training_frame(sales, frames["inventory"], frames["purchase_orders"], horizon_days=7)
        report["stockout"] = stockout_eval(tr) if not tr.empty else {"skipped": "empty training frame"}
        report["stockout"]["training_rows"] = int(len(tr))

    # Supplier delay classifier
    if "purchase_orders" in frames:
        report["supplier_risk"] = supplier_eval(frames["purchase_orders"])

    # Anomaly detector P/R using labelled events
    if "labels_ground_truth" in frames:
        labels = frames["labels_ground_truth"].copy()
        labels["payload"] = labels["payload"].apply(json.loads)
        spike_rows = [l["payload"] for _, l in labels.iterrows() if l["event_type"] == "DEMAND_SPIKE"]
        decline_rows = [l["payload"] for _, l in labels.iterrows() if l["event_type"] == "DEMAND_DECLINE"]
        meta_path = _data_dir() / "_meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        start = pd.to_datetime(meta.get("start_date", "2026-01-01")).date()

        # Evaluate on 10 random affected (pid, sid) that have labels
        rng = random.Random(42)
        groups: dict[tuple[str, str], dict[str, set]] = {}
        for row in spike_rows:
            groups.setdefault((row["product_id"], row["store_id"]), {"spike": set(), "decline": set()})
            d = start + pd.Timedelta(days=int(row["day"]))
            groups[(row["product_id"], row["store_id"])]["spike"].add(d.date() if hasattr(d, "date") else d)
        for row in decline_rows:
            groups.setdefault((row["product_id"], row["store_id"]), {"spike": set(), "decline": set()})
            d = start + pd.Timedelta(days=int(row["day"]))
            groups[(row["product_id"], row["store_id"])]["decline"].add(d.date() if hasattr(d, "date") else d)
        chosen = rng.sample(list(groups.items()), k=min(10, len(groups)))
        prec = []
        rec_ = []
        f1_ = []
        for (pid, sid), lab in chosen:
            hist = product_store_daily(sales, pid, sid)
            if hist.empty:
                continue
            m = evaluate_precision_recall(hist, lab["spike"], lab["decline"], z_threshold=2.5)
            prec.append(m["precision"])
            rec_.append(m["recall"])
            f1_.append(m["f1"])
        report["anomaly_detection"] = {
            "detector": "rolling_zscore(window=28, threshold=2.5)",
            "evaluated_pairs": len(chosen),
            "mean_precision": round(float(np.mean(prec)) if prec else 0.0, 4),
            "mean_recall": round(float(np.mean(rec_)) if rec_ else 0.0, 4),
            "mean_f1": round(float(np.mean(f1_)) if f1_ else 0.0, 4),
        }

    # Write
    out = out_path or (
        Path(__file__).resolve().parent.parent.parent.parent / "ml" / "evaluation" / "report.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    r = run_evaluation()
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
