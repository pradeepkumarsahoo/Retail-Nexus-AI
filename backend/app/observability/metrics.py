# Author: Pradeep Sahoo — Retail Nexus AI
"""Prometheus metrics for API, agents and ML."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQ_COUNT = Counter(
    "ct_http_requests_total", "HTTP requests total",
    ("method", "path", "status"),
)
REQ_LATENCY = Histogram(
    "ct_http_request_latency_seconds", "HTTP request latency",
    ("method", "path"),
)
AGENT_RUN_COUNT = Counter(
    "ct_agent_runs_total", "Agent runs total", ("provider", "status"),
)
AGENT_RUN_LATENCY = Histogram(
    "ct_agent_run_latency_seconds", "Agent run latency",
)
TOOL_FAIL = Counter("ct_tool_failures_total", "Agent tool failures", ("tool",))
EXCEPTIONS_OPEN = Gauge("ct_exceptions_open", "Open exceptions", ("severity",))


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
