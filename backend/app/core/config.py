# Author: Pradeep Sahoo — Retail Nexus AI
"""Application configuration via environment variables."""
from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-me-32-chars-min"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./control_tower.db"
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "mock"
    llm_model: str = "mock-small"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"

    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    agent_max_steps: int = 12
    agent_step_timeout_seconds: int = 20
    agent_max_retries: int = 2

    log_level: str = "INFO"
    log_format: str = "json"
    otel_service_name: str = "control-tower-backend"
    otel_exporter_otlp_endpoint: str | None = None

    rate_limit_ingest: int = 30
    rate_limit_investigation: int = 60

    random_seed: int = Field(default=42)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
