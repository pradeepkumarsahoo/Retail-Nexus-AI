# Author: Pradeep Sahoo — Retail Nexus AI
"""LLM provider abstraction.

Default: deterministic mock. The mock reads a prompt and returns a template-filled
JSON response based on the task; this keeps the entire stack runnable without
network access while still exercising the agent code paths.

Alternate providers (openai, bedrock) are wired behind the same interface. They
are not exercised by tests unless credentials are present — the mock path is the
contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.security.sanitize import strip_untrusted, contains_prompt_injection


@dataclass
class LLMResponse:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    provider: str
    model: str
    latency_ms: int


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> LLMResponse:
        """Return a response whose `.text` is a JSON string valid against the hint."""


# ---- mock provider ---------------------------------------------------------

class MockLLM(LLMProvider):
    name = "mock"
    model = "mock-small"

    # Cost model purely illustrative (not real).
    COST_PER_1K_IN = 0.0
    COST_PER_1K_OUT = 0.0

    def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> LLMResponse:
        safe_user = strip_untrusted(user)
        start = time.perf_counter()
        if contains_prompt_injection(safe_user) or contains_prompt_injection(system):
            # The mock refuses to echo injected directives.
            payload = {"error": "prompt_injection_refused", "message": "ignored embedded directive"}
        else:
            payload = self._deterministic_reply(system, safe_user, schema_hint)
        text = json.dumps(payload)
        latency = int((time.perf_counter() - start) * 1000)
        tokens_in = max(1, len(safe_user) // 4)
        tokens_out = max(1, len(text) // 4)
        return LLMResponse(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=0.0,
            provider=self.name,
            model=self.model,
            latency_ms=latency,
        )

    def _deterministic_reply(self, system: str, user: str, schema_hint: str | None) -> dict[str, Any]:
        # The mock's job is to produce a *reasonable* interpretation of the structured
        # evidence that the deterministic engines already computed. The agent code
        # passes those numbers inside `user`; the mock turns them back into prose plus
        # a decision rationale.
        try:
            parsed = json.loads(user)
            evidence = parsed.get("evidence", parsed)
        except Exception:
            evidence = {"raw_input": user[:400]}
        system_hash = hashlib.sha1(system.encode("utf-8")).hexdigest()[:6]
        return {
            "rationale": self._compose_rationale(evidence),
            "signals": evidence,
            "confidence": self._confidence_from(evidence),
            "mock_system_hash": system_hash,
        }

    @staticmethod
    def _compose_rationale(e: dict[str, Any]) -> str:
        # A tiny grammar — crisp English assembled from numbers already in evidence.
        bits: list[str] = []
        if "probability" in e:
            p = float(e["probability"])
            if p >= 0.75:
                bits.append(f"Stockout risk is CRITICAL (p={p:.2f}).")
            elif p >= 0.5:
                bits.append(f"Stockout risk is HIGH (p={p:.2f}).")
            elif p >= 0.25:
                bits.append(f"Stockout risk is MEDIUM (p={p:.2f}).")
            else:
                bits.append(f"Stockout risk is low (p={p:.2f}).")
        if "days_of_supply" in e:
            bits.append(f"Days of supply = {e['days_of_supply']}.")
        if "supplier_otd_avg" in e:
            otd = float(e["supplier_otd_avg"])
            if otd < 0.8:
                bits.append(f"Supplier OTD avg {otd:.2f} indicates elevated supply-side risk.")
            else:
                bits.append(f"Supplier OTD avg {otd:.2f} is adequate.")
        if "z_score" in e:
            z = float(e["z_score"])
            if abs(z) >= 3:
                bits.append(f"Demand z-score of {z:.2f} is extreme.")
            else:
                bits.append(f"Demand z-score of {z:.2f}.")
        if "stats" in e and isinstance(e["stats"], dict):
            s = e["stats"]
            if "on_time_delivery_pct" in s:
                bits.append(f"OTD = {float(s['on_time_delivery_pct']):.2%}.")
            if "avg_lead_time_days" in s:
                bits.append(f"Avg lead-time = {float(s['avg_lead_time_days']):.1f} days.")
        if not bits:
            bits.append("Evidence recorded; action required by orchestrator.")
        return " ".join(bits)

    @staticmethod
    def _confidence_from(e: dict[str, Any]) -> float:
        if "probability" in e:
            try:
                return round(float(e["probability"]), 3)
            except Exception:
                return 0.5
        if "stats" in e and isinstance(e["stats"], dict) and "on_time_delivery_pct" in e["stats"]:
            return round(1.0 - float(e["stats"]["on_time_delivery_pct"]), 3)
        if "z_score" in e:
            return round(min(1.0, abs(float(e["z_score"])) / 5.0), 3)
        return 0.5


# ---- openai / bedrock stubs ------------------------------------------------

class OpenAICompatibleLLM(LLMProvider):
    name = "openai"
    model = "gpt-4o-mini"

    def __init__(self) -> None:
        import httpx
        self.client = httpx.Client(timeout=30.0)
        self.model = os.getenv("LLM_MODEL", self.model)
        self.base = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        self.key = os.getenv("OPENAI_API_KEY") or ""
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY is not set")

    def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> LLMResponse:
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        r = self.client.post(
            f"{self.base}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.key}"},
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
            cost_usd=0.0,
            provider=self.name,
            model=self.model,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )


class BedrockLLM(LLMProvider):
    name = "bedrock"
    model = "anthropic.claude-3-haiku-20240307-v1:0"

    def __init__(self) -> None:
        try:
            import boto3  # type: ignore
        except ImportError as e:
            raise RuntimeError("boto3 is required for the bedrock provider") from e
        self.client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.model = os.getenv("BEDROCK_MODEL_ID", self.model)

    def complete_json(self, system: str, user: str, schema_hint: str | None = None) -> LLMResponse:
        start = time.perf_counter()
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        })
        resp = self.client.invoke_model(modelId=self.model, body=body)
        raw = json.loads(resp["body"].read())
        text = raw.get("content", [{}])[0].get("text", "{}")
        return LLMResponse(
            text=text,
            tokens_in=raw.get("usage", {}).get("input_tokens", 0),
            tokens_out=raw.get("usage", {}).get("output_tokens", 0),
            cost_usd=0.0,
            provider=self.name,
            model=self.model,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )


def get_provider() -> LLMProvider:
    s = get_settings()
    name = (s.llm_provider or "mock").lower()
    try:
        if name == "mock":
            return MockLLM()
        if name == "openai":
            return OpenAICompatibleLLM()
        if name == "bedrock":
            return BedrockLLM()
    except Exception as e:
        # Fail safe: fall back to mock. The caller sees provider=mock in the trace.
        from app.core.logging import get_logger
        get_logger("llm").warning("provider_fallback", requested=name, error=str(e))
        return MockLLM()
    return MockLLM()
