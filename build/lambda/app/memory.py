"""Cross-session memory: durable preferences/contacts/facts with semantic recall.

Embeddings come from the configured LLM (Titan on Bedrock, hashed vectors in
mock mode). Recall is cosine similarity — fine at personal-assistant scale; the
same records would move to pgvector / OpenSearch if this grew multi-tenant.
"""
from __future__ import annotations

import math

from app.llm.base import LLMClient
from app.models import MemoryRecord
from app.store.base import Store


class MemoryService:
    def __init__(self, store: Store, llm: LLMClient) -> None:
        self._store = store
        self._llm = llm

    def remember(self, text: str, kind: str = "fact") -> MemoryRecord:
        record = MemoryRecord(kind=kind, text=text, embedding=self._llm.embed(text))
        return self._store.save_memory(record)

    def recall(self, query: str, k: int = 4) -> list[MemoryRecord]:
        records = self._store.list_memory()
        if not records:
            return []
        q = self._llm.embed(query)
        scored = [
            (self._cosine(q, r.embedding), r) for r in records if r.embedding
        ]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [r for _, r in scored[:k]]

    def all(self) -> list[MemoryRecord]:
        return sorted(self._store.list_memory(), key=lambda r: r.created_at)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0
