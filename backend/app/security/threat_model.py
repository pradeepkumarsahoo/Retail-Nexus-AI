# Author: Pradeep Sahoo — Retail Nexus AI
"""OWASP Top 7 threat-modeling layer for LLM-powered agents.

Codifies the seven most load-bearing items from OWASP's Top 10 for LLM
Applications so every specialist agent runs the same pre- and post-flight
checks before composing evidence. The layer is defensive (deny-by-default on
violations in strict mode, redact-and-annotate in soft mode) and produces a
machine-readable audit trail on `AgentState` for downstream observability.

Checks implemented:

    LLM01  Prompt Injection              — scan system+user prompts and any
                                            untrusted free-text in exception
                                            evidence for jailbreak patterns.
    LLM02  Sensitive Information Disc.   — redact PII/secrets from inputs
                                            and outputs before they are logged
                                            or persisted onto the state.
    LLM03  Supply Chain                  — pin the LLM provider+model and
                                            reject tool names outside the
                                            allow-list (defense-in-depth with
                                            `sanitize.validate_tool_call`).
    LLM04  Data & Model Poisoning        — bound-check numeric evidence
                                            (probabilities in [0,1], no NaN/Inf,
                                            no absurd magnitudes) so a corrupted
                                            upstream feature cannot drive a
                                            recommendation.
    LLM05  Improper Output Handling      — validate the LLM's JSON output
                                            against an expected shape and
                                            clip string sizes before use.
    LLM06  Excessive Agency              — enforce an agent-level scope list:
                                            an agent may only call tools in
                                            its declared capability set.
    LLM07  System Prompt Leakage         — strip fragments of the system
                                            prompt that the model might have
                                            echoed back in its rationale.

Usage (per agent):

    guard = ThreatGuard(agent="demand_agent",
                        allowed_tools={"forecast_demand"},
                        provider=llm.name, model=llm.model)
    guard.preflight(state, system=SYSTEM_BASE, user_payload=evidence_payload)
    # ... call LLM / tools ...
    rationale = guard.sanitize_output(rationale, system=SYSTEM_BASE)
    guard.record(state)
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from app.security.sanitize import (
    ALLOWED_TOOL_ARGS,
    contains_prompt_injection,
    redact_sensitive,
    strip_untrusted,
)

# ---- Provider / model allow-list (LLM03) -----------------------------------

APPROVED_PROVIDERS: dict[str, set[str]] = {
    "mock": {"mock-small", "mock-medium"},
    "openai": {"gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"},
    "bedrock": {
        "anthropic.claude-3-haiku-20240307-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
    },
}

# PII patterns beyond the credential scrubber in sanitize.redact_sensitive.
_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "[CARD_REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b(?:\+?\d{1,3}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b"), "[PHONE_REDACTED]"),
]

# Numeric sanity bounds for evidence payloads (LLM04).
_PROBABILITY_KEYS = {"probability", "confidence", "demand_cv", "supplier_otd_avg"}
_NON_NEGATIVE_KEYS = {
    "mean_daily", "mean_daily_demand", "unit_price", "unit_cost",
    "revenue_at_risk", "expected_expedite_cost", "expected_transfer_cost",
    "horizon_days", "days_of_supply",
}
_MAGNITUDE_CEILING = 1e12

# Strings this project would never want leaked verbatim in an LLM response.
_SYSTEM_PROMPT_LEAK_HINTS = (
    "you are a supply chain analyst",
    "deterministic engines; do not alter",
    "reply with json only",
)


class ThreatViolation(Exception):
    """Raised in strict mode when a threat check fails hard."""


@dataclass
class ThreatFinding:
    code: str            # e.g. "LLM01", "LLM04"
    severity: str        # "info" | "warn" | "high"
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "detail": self.detail,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class ThreatGuard:
    """Per-agent OWASP Top 7 guard.

    `strict=True` raises `ThreatViolation` on a high-severity finding; the
    default (soft mode) records the finding and returns a sanitized payload so
    the agent can continue to produce safe evidence.
    """

    agent: str
    allowed_tools: set[str]
    provider: str
    model: str
    strict: bool = False
    findings: list[ThreatFinding] = field(default_factory=list)

    # -- lifecycle ----------------------------------------------------------

    def preflight(
        self,
        state: Any,
        *,
        system: str,
        user_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run LLM01/03/04/06 checks against the inputs about to be sent."""
        self._check_prompt_injection(system, user_payload or {})
        self._check_supply_chain()
        self._check_excessive_agency(state)
        safe_payload = self._bound_check_evidence(user_payload or {})
        safe_payload = self._redact_pii(safe_payload)
        return safe_payload

    def guard_tool_call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """LLM03 + LLM06: tool name must be allow-listed globally and
        in the agent's declared scope. Args are re-validated for shape."""
        if tool not in ALLOWED_TOOL_ARGS:
            self._emit("LLM03", "high", f"tool {tool!r} not in global allow-list")
        if tool not in self.allowed_tools:
            self._emit("LLM06", "high",
                       f"agent {self.agent!r} not authorized to call {tool!r}",
                       detail={"allowed": sorted(self.allowed_tools)})
        allowed_args = ALLOWED_TOOL_ARGS.get(tool, set())
        extra = set(args) - allowed_args
        if extra:
            self._emit("LLM05", "warn",
                       f"dropping unexpected args for {tool!r}",
                       detail={"extra": sorted(extra)})
        return {k: v for k, v in args.items() if k in allowed_args}

    def sanitize_output(self, text: str, *, system: str) -> str:
        """LLM02 + LLM05 + LLM07 post-flight: redact PII/secrets, bound size,
        strip any echo of the system prompt."""
        if text is None:
            return ""
        text = str(text)
        if len(text) > 4000:
            self._emit("LLM05", "warn", "output truncated",
                       detail={"original_len": len(text)})
            text = text[:4000]
        # LLM02 — secrets and PII.
        before = text
        text = redact_sensitive(text)
        text = self._scrub_pii_text(text)
        if text != before:
            self._emit("LLM02", "warn", "pii or secret pattern redacted from output")
        # LLM07 — system prompt leakage.
        lowered = text.lower()
        for hint in _SYSTEM_PROMPT_LEAK_HINTS:
            if hint in lowered:
                self._emit("LLM07", "warn",
                           "system-prompt fragment appeared in output",
                           detail={"hint": hint})
                text = re.sub(re.escape(hint), "[REDACTED_SYSTEM]", text,
                              flags=re.IGNORECASE)
                lowered = text.lower()
        # Additional LLM07 — reject raw system content leak.
        if system and len(system) > 32 and system[:32].lower() in lowered:
            self._emit("LLM07", "high", "verbatim system prompt detected in output")
            text = text.replace(system[:32], "[REDACTED_SYSTEM]")
        return text

    def record(self, state: Any) -> None:
        """Attach findings to the agent state for the audit trail."""
        if not self.findings:
            return
        bag = getattr(state, "security_findings", None)
        serialized = [f.to_dict() for f in self.findings]
        if isinstance(bag, list):
            bag.extend(serialized)
            return
        # Fallback: persist onto the last step's outputs so the trace keeps it.
        steps = getattr(state, "steps", None)
        if steps:
            last = steps[-1]
            outputs = getattr(last, "outputs", None)
            if isinstance(outputs, dict):
                outputs.setdefault("security_findings", []).extend(serialized)

    # -- individual checks --------------------------------------------------

    def _check_prompt_injection(self, system: str, user_payload: dict[str, Any]) -> None:
        """LLM01 — scan every string we're about to feed the model."""
        suspects: list[str] = []
        for key, val in self._iter_strings(user_payload):
            if contains_prompt_injection(val):
                suspects.append(key)
        if contains_prompt_injection(system or ""):
            suspects.append("system")
        if suspects:
            self._emit("LLM01", "high",
                       "prompt-injection patterns detected; directives ignored",
                       detail={"fields": suspects})

    def _check_supply_chain(self) -> None:
        """LLM03 — refuse to run under an unknown provider/model pair."""
        approved_models = APPROVED_PROVIDERS.get(self.provider.lower())
        if approved_models is None:
            self._emit("LLM03", "high",
                       "llm provider is not in the approved list",
                       detail={"provider": self.provider})
            return
        if self.model not in approved_models:
            self._emit("LLM03", "warn",
                       "llm model is outside the pinned set for this provider",
                       detail={"provider": self.provider, "model": self.model})

    def _check_excessive_agency(self, state: Any) -> None:
        """LLM06 — sanity-check the agent's scope declaration."""
        if not self.allowed_tools:
            self._emit("LLM06", "info",
                       f"agent {self.agent!r} declares no tool scope (read-only)")
        # If the state carries a tenant/user context, enforce they have not
        # escalated to a role the agent should not be acting on behalf of.
        risk_tier = getattr(state, "risk_tier", None)
        if risk_tier == "CRITICAL" and not getattr(state, "requires_approval", True):
            self._emit("LLM06", "high",
                       "critical-tier state reached an agent without approval gate",
                       detail={"risk_tier": risk_tier})

    def _bound_check_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        """LLM04 — reject NaN/Inf, clamp probabilities, drop absurd magnitudes."""
        out: dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, dict):
                out[k] = self._bound_check_evidence(v)
                continue
            if isinstance(v, (list, tuple)):
                out[k] = [self._clean_scalar(k, x) for x in v]
                continue
            out[k] = self._clean_scalar(k, v)
        return out

    def _clean_scalar(self, key: str, v: Any) -> Any:
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, (int, float)):
            f = float(v)
            if math.isnan(f) or math.isinf(f):
                self._emit("LLM04", "high",
                           "non-finite numeric evidence replaced with 0",
                           detail={"field": key, "value": repr(v)})
                return 0.0
            if abs(f) > _MAGNITUDE_CEILING:
                self._emit("LLM04", "high",
                           "evidence magnitude exceeds sanity ceiling",
                           detail={"field": key, "value": f})
                return math.copysign(_MAGNITUDE_CEILING, f)
            if key in _PROBABILITY_KEYS and (f < 0.0 or f > 1.0):
                self._emit("LLM04", "warn",
                           "probability outside [0,1] clamped",
                           detail={"field": key, "value": f})
                return max(0.0, min(1.0, f))
            if key in _NON_NEGATIVE_KEYS and f < 0:
                self._emit("LLM04", "warn",
                           "negative value for non-negative field clamped",
                           detail={"field": key, "value": f})
                return 0.0
            return f
        return v

    def _redact_pii(self, payload: dict[str, Any]) -> dict[str, Any]:
        """LLM02 — walk the payload and redact PII/secrets in free-text."""
        def _walk(x: Any) -> Any:
            if isinstance(x, dict):
                return {k: _walk(v) for k, v in x.items()}
            if isinstance(x, (list, tuple)):
                return [_walk(v) for v in x]
            if isinstance(x, str):
                scrubbed = self._scrub_pii_text(redact_sensitive(strip_untrusted(x)))
                if scrubbed != x:
                    self._emit("LLM02", "info", "pii pattern redacted from input")
                return scrubbed
            return x

        return _walk(payload)  # type: ignore[return-value]

    def _scrub_pii_text(self, text: str) -> str:
        out = text
        for pat, repl in _PII_PATTERNS:
            out = pat.sub(repl, out)
        return out

    # -- helpers ------------------------------------------------------------

    def _emit(self, code: str, severity: str, message: str,
              detail: dict[str, Any] | None = None) -> None:
        self.findings.append(ThreatFinding(code=code, severity=severity,
                                           message=message, detail=detail or {}))
        if self.strict and severity == "high":
            raise ThreatViolation(f"[{code}] {message}")

    def _iter_strings(self, obj: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
        if isinstance(obj, str):
            yield prefix or "<root>", obj
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from self._iter_strings(v, f"{prefix}.{k}" if prefix else str(k))
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                yield from self._iter_strings(v, f"{prefix}[{i}]")


# ---- Per-agent scope registry ---------------------------------------------

AGENT_TOOL_SCOPE: dict[str, set[str]] = {
    "demand_agent":        {"forecast_demand"},
    "inventory_agent":     {"stockout_probability", "find_transfer_candidates"},
    "supplier_agent":      {"supplier_reliability", "find_alt_suppliers"},
    "alt_sourcing_agent":  {"find_alt_suppliers"},
    "business_impact_agent": {"lookup_product"},
}


def guard_for(agent: str, llm_name: str, llm_model: str, strict: bool = False) -> ThreatGuard:
    """Factory used by each specialist agent."""
    return ThreatGuard(
        agent=agent,
        allowed_tools=AGENT_TOOL_SCOPE.get(agent, set()),
        provider=llm_name,
        model=llm_model,
        strict=strict,
    )
