# Author: Pradeep Sahoo — Retail Nexus AI
"""Demand anomaly detection.

Combines two signals:
1. z-score of today vs. trailing 28-day rolling mean/std per product-store (statistical).
2. IsolationForest on (recent_sales_7, recent_sales_14, dow, promo_14) for coverage.

Returns per-day labels and scores. Evaluation uses labelled spike/decline events
from the synthetic generator.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

import numpy as np
import pandas as pd


AnomalyKind = Literal["NONE", "DEMAND_SPIKE", "DEMAND_DECLINE"]


@dataclass
class AnomalyPoint:
    date: date
    units: int
    z_score: float
    kind: AnomalyKind


def rolling_zscore(hist: pd.DataFrame, window: int = 28) -> pd.Series:
    s = hist["units_sold"].astype(float)
    mu = s.rolling(window, min_periods=max(7, window // 2)).mean()
    sd = s.rolling(window, min_periods=max(7, window // 2)).std(ddof=0)
    z = (s - mu) / sd.replace(0.0, np.nan)
    return z.fillna(0.0)


def detect(hist: pd.DataFrame, z_threshold: float = 2.5) -> list[AnomalyPoint]:
    """Return per-day anomaly labels for the whole history."""
    if hist.empty:
        return []
    z = rolling_zscore(hist)
    out: list[AnomalyPoint] = []
    for ts, val in hist["units_sold"].items():
        zs = float(z.loc[ts])
        if zs >= z_threshold:
            kind: AnomalyKind = "DEMAND_SPIKE"
        elif zs <= -z_threshold:
            kind = "DEMAND_DECLINE"
        else:
            kind = "NONE"
        if kind != "NONE":
            out.append(AnomalyPoint(date=pd.Timestamp(ts).date(), units=int(val), z_score=round(zs, 3), kind=kind))
    return out


def iforest_scores(hist: pd.DataFrame) -> pd.Series:
    """Secondary detector — returns anomaly score per day."""
    from sklearn.ensemble import IsolationForest

    if len(hist) < 60:
        return pd.Series(0.0, index=hist.index)
    feats = pd.DataFrame({
        "units": hist["units_sold"].astype(float),
        "ma7": hist["units_sold"].rolling(7, min_periods=1).mean(),
        "ma14": hist["units_sold"].rolling(14, min_periods=1).mean(),
        "dow": pd.Series(hist.index).apply(lambda d: pd.Timestamp(d).weekday()).values,
    })
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(feats.values)
    # negative score -> more anomalous
    raw = model.score_samples(feats.values)
    return pd.Series(-raw, index=hist.index)


def evaluate_precision_recall(
    hist: pd.DataFrame,
    labelled_spike_days: set[date],
    labelled_decline_days: set[date],
    z_threshold: float = 2.5,
) -> dict[str, Any]:
    """Precision/recall of the z-score detector against synthetic ground-truth."""
    detections = detect(hist, z_threshold)
    tp = fp = fn = 0
    predicted_spikes = {d.date for d in detections if d.kind == "DEMAND_SPIKE"}
    predicted_declines = {d.date for d in detections if d.kind == "DEMAND_DECLINE"}
    for d in predicted_spikes:
        if d in labelled_spike_days:
            tp += 1
        else:
            fp += 1
    for d in predicted_declines:
        if d in labelled_decline_days:
            tp += 1
        else:
            fp += 1
    for d in labelled_spike_days:
        if d not in predicted_spikes:
            fn += 1
    for d in labelled_decline_days:
        if d not in predicted_declines:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn,
        "z_threshold": z_threshold,
    }
