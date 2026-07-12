"""Amazon Bedrock LLM client — Claude via the Converse API, Titan for embeddings."""
from __future__ import annotations

import json
import logging

import boto3

logger = logging.getLogger(__name__)


class BedrockLLM:
    provider = "bedrock"

    def __init__(self, region: str, model_id: str, embed_model_id: str) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._model_id = model_id
        self._embed_model_id = embed_model_id

    def complete(self, system: str, prompt: str, *, max_tokens: int = 1024,
                 temperature: float = 0.2) -> str:
        resp = self._client.converse(
            modelId=self._model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        parts = resp["output"]["message"]["content"]
        return "".join(p.get("text", "") for p in parts).strip()

    def embed(self, text: str) -> list[float]:
        resp = self._client.invoke_model(
            modelId=self._embed_model_id,
            body=json.dumps({"inputText": text[:8000]}),
        )
        payload = json.loads(resp["body"].read())
        return payload["embedding"]
