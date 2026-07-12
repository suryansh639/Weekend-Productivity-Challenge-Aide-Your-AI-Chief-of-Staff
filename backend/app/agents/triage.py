"""Triage worker: classify an inbox item and draft a reply if one is needed."""
from __future__ import annotations

import logging

from app.agents.prompts import TRIAGE_SYSTEM, item_prompt
from app.llm.base import LLMClient, extract_json
from app.models import InboxItem, Priority

logger = logging.getLogger("aide.triage")

_VALID = {p.value for p in Priority}


class TriageAgent:
    def __init__(self, llm: LLMClient, owner: str) -> None:
        self._llm = llm
        self._system = TRIAGE_SYSTEM.format(owner=owner)

    def triage(self, item: InboxItem) -> tuple[InboxItem, str]:
        """Classify the item in place and return ``(item, draft_reply)``."""
        try:
            raw = self._llm.complete(self._system, item_prompt(item),
                                     max_tokens=700, temperature=0.1)
            data = extract_json(raw)
        except Exception:  # noqa: BLE001 - never let one bad item break the batch
            logger.exception("triage failed for %s; applying safe default", item.id)
            data = {}

        priority = data.get("priority")
        item.priority = Priority(priority) if priority in _VALID else Priority.P2
        item.category = data.get("category") or "general"
        item.needs_response = bool(data.get("needs_response", False))
        item.summary = data.get("summary") or item.subject
        item.reasoning = data.get("reasoning") or ""
        item.triaged = True
        draft_reply = (data.get("draft_reply") or "").strip()
        return item, draft_reply
