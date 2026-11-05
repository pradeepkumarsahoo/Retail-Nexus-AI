# Author: Pradeep Sahoo — Retail Nexus AI
"""Prompt-injection defenses and tool-argument validation for LLM inputs."""
from __future__ import annotations

import re
from typing import Any

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |the )?(previous|prior|above) (instructions|rules|system)", re.I),
    re.compile(r"disregard (all |the )?(previous|prior|above)", re.I),
    re.compile(r"you are now (?:a|an) (?:dan|developer mode|unrestricted)", re.I),
    re.compile(r"system[: ]+prompt", re.I),
    re.compile(r"```(?:system|developer)\b", re.I),
]

_SENSITIVE_TOKENS = re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)[:= ]+\S+")


def contains_prompt_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def redact_sensitive(text: str) -> str:
    return _SENSITIVE_TOKENS.sub(r"\1=[REDACTED]", text)


def strip_untrusted(text: str, max_length: int = 4000) -> str:
    """Normalize external text before handing it to an LLM.

    Treats retrieved documents and user-provided free-text as untrusted.
    """
    if text is None:
        return ""
    text = str(text)[:max_length]
    text = redact_sensitive(text)
    # Flatten obvious directive patterns so they lose instructional force.
    text = re.sub(r"(?im)^\s*(system|assistant|developer)\s*:\s*", r"[\1]: ", text)
    return text


ALLOWED_TOOL_ARGS: dict[str, set[str]] = {
    "lookup_product": {"product_id"},
    "lookup_store": {"store_id"},
    "lookup_supplier": {"supplier_id"},
    "forecast_demand": {"product_id", "store_id", "horizon_days"},
    "stockout_probability": {"product_id", "store_id", "horizon_days"},
    "supplier_reliability": {"supplier_id"},
    "find_alt_suppliers": {"product_id"},
    "find_transfer_candidates": {"product_id", "store_id"},
    "simulate_scenario": {"exception_id", "scenario"},
}


def validate_tool_call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    allowed = ALLOWED_TOOL_ARGS.get(tool)
    if allowed is None:
        raise ValueError(f"Tool {tool!r} is not allow-listed")
    extra = set(args.keys()) - allowed
    if extra:
        raise ValueError(f"Tool {tool!r} received unexpected args: {sorted(extra)}")
    return {k: args[k] for k in args.keys() if k in allowed}
