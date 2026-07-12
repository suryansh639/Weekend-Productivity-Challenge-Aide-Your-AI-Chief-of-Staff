"""Proactive nudge agent: finds threads that have gone quiet past a threshold and
drafts a follow-up nudge as a *pending* action. Runs on a schedule (EventBridge),
not on user demand — this is the "proactive, not reactive" capability.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.prompts import NUDGE_SYSTEM, item_prompt
from app.llm.base import LLMClient, extract_json
from app.models import Action, ActionType, InboxItem

logger = logging.getLogger("aide.nudges")


class NudgeAgent:
    def __init__(self, llm: LLMClient, owner: str, stale_days: int) -> None:
        self._llm = llm
        self._owner = owner
        self._stale_days = stale_days
        self._system = NUDGE_SYSTEM.format(owner=owner)

    def find_stale(self, items: list[InboxItem]) -> list[InboxItem]:
        now = datetime.now(timezone.utc)
        stale = []
        for item in items:
            since = item.awaiting_reply_since
            if since and (now - since).days >= self._stale_days:
                stale.append(item)
        return stale

    def draft_nudge(self, item: InboxItem) -> Action:
        try:
            data = extract_json(
                self._llm.complete(self._system, item_prompt(item), max_tokens=400)
            )
            body = data.get("body", "")
        except Exception:  # noqa: BLE001
            logger.exception("nudge draft failed for %s", item.id)
            body = f"Just following up on \"{item.subject}\" — any thoughts?"
        days = (datetime.now(timezone.utc) - item.awaiting_reply_since).days \
            if item.awaiting_reply_since else 0
        return Action(
            type=ActionType.SEND_NUDGE,
            title=f"Nudge on \"{item.subject}\"",
            payload={"to": item.sender_email, "subject": f"Re: {item.subject}",
                     "body": body},
            rationale=f"No reply for {days} days on this thread.",
            source_item_id=item.id,
        )
