"""Application configuration, loaded from environment variables.

Every setting has a safe local default so the app runs offline out of the box.
Set ``AIDE_LLM_PROVIDER=bedrock`` and ``AIDE_STORE_BACKEND=dynamo`` to go live on AWS.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AIDE_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Providers
    llm_provider: str = "mock"          # "mock" | "bedrock"
    store_backend: str = "local"        # "local" | "dynamo"

    # Local store
    local_db_path: str = ".aide_data.json"

    # AWS / Bedrock
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.amazon.nova-lite-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    dynamo_table: str = "aide"

    # Behaviour
    nudge_stale_days: int = 3
    owner_email: str = "you@example.com"
    owner_name: str = "You"

    # API
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
