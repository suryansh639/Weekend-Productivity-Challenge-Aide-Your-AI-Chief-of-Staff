"""LLM client protocol.

The rest of the app depends only on this interface, so we can run against a
deterministic mock offline and Amazon Bedrock (Nova + Titan) in production
without changing a single line of agent code.
"""
from __future__ import annotations

import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, prompt: str, *, max_tokens: int = 1024,
                 temperature: float = 0.2) -> str:
        """Return a single text completion."""
        ...

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for semantic memory recall."""
        ...


def extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from an LLM response.

    The model occasionally wraps JSON in prose or fenced code blocks; we recover the
    first balanced ``{...}`` block so callers get structured data reliably.
    """
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in LLM output")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced JSON in LLM output")
