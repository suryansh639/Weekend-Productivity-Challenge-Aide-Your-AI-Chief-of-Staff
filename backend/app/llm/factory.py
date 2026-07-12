"""Select the LLM client based on configuration."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMClient


@lru_cache
def get_llm() -> LLMClient:
    settings = get_settings()
    if settings.llm_provider == "bedrock":
        from app.llm.bedrock import BedrockLLM

        return BedrockLLM(
            region=settings.aws_region,
            model_id=settings.bedrock_model_id,
            embed_model_id=settings.bedrock_embed_model_id,
        )
    from app.llm.mock import MockLLM

    return MockLLM()
