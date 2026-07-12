"""Application service — the use-case layer the API and Lambdas call into.

Coordinates connectors, agents, memory and the store, and (critically) enforces
the human-in-the-loop gate: agents *propose* actions, users approve/veto, and only
then does an action get executed by a connector.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from app.agents.nudges import NudgeAgent
from app.agents.supervisor import ChiefOfStaffSupervisor
from app.agents.triage import TriageAgent
from app.config import get_settings
from app.connectors.demo import DemoConnector, DemoExecutor
from app.llm import get_llm
from app.memory import MemoryService
from app.models import (Action, ActionStatus, ActionType, Briefing, InboxItem,
                        Priority)
from app.store import get_store

logger = logging.getLogger("aide.service")

_ATTENTION = {Priority.P0, Priority.P1}
_DEFAULT_MEMORY = [
    ("preference", "Prefers concise, warm replies signed 'You'. No corporate jargon."),
    ("preference", "Investor updates and customer issues are always top priority."),
    ("contact", "Dana Reyes (Northstar VC) is leading our Series A — high priority."),
    ("preference", "Deprioritize newsletters and automated digests; never auto-reply."),
]


class AideService:
    def __init__(self) -> None:
        s = get_settings()
        self._settings = s
        self._store = get_store()
        self._llm = get_llm()
        self._memory = MemoryService(self._store, self._llm)
        self._source = DemoConnector()
        self._executor = DemoExecutor()
        self._triage = TriageAgent(self._llm, s.owner_name)
        self._supervisor = ChiefOfStaffSupervisor(
            self._store, self._memory, self._llm, s.owner_name)
        self._nudges = NudgeAgent(self._llm, s.owner_name, s.nudge_stale_days)

    # ─── natural key for dedupe on sync ───────────────────────────────────────
    @staticmethod
    def _key(item: InboxItem) -> str:
        return f"{item.channel.value}:{item.thread_id}:{item.subject}"

    # ─── seeding & sync ───────────────────────────────────────────────────────
    def seed_demo(self) -> dict:
        self._store.reset()
        for kind, text in _DEFAULT_MEMORY:
            self._memory.remember(text, kind=kind)
        count = self.sync_inbox()
        return {"seeded_items": count, "memory": len(_DEFAULT_MEMORY)}

    def sync_inbox(self) -> int:
        """Fetch from the connector, triage new items, stage draft replies."""
        existing = {self._key(i) for i in self._store.list_items()}
        new_count = 0
        for item in self._source.fetch():
            if self._key(item) in existing:
                continue
            item, draft = self._triage.triage(item)
            self._store.upsert_item(item)
            new_count += 1
            self._maybe_stage_reply(item, draft)
        logger.info("sync_inbox: %d new items", new_count)
        return new_count

    def _maybe_stage_reply(self, item: InboxItem, draft: str) -> None:
        """Auto-stage a *pending* draft reply for urgent items needing a response."""
        if not (item.needs_response and item.priority in _ATTENTION and draft):
            return
        if any(a.source_item_id == item.id and a.type == ActionType.SEND_REPLY
               for a in self._store.list_actions()):
            return
        self._store.save_action(Action(
            type=ActionType.SEND_REPLY,
            title=f"Reply to {item.sender}: {item.subject}",
            payload={"to": item.sender_email, "subject": f"Re: {item.subject}",
                     "body": draft},
            rationale=f"{item.priority.value} item that needs a response.",
            source_item_id=item.id,
        ))

    # ─── reads ────────────────────────────────────────────────────────────────
    def list_inbox(self) -> list[InboxItem]:
        return self._store.list_items()

    def attention_queue(self) -> list[InboxItem]:
        order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}
        items = [i for i in self._store.list_items()
                 if i.triaged and (i.priority in _ATTENTION or i.needs_response)]
        return sorted(items, key=lambda i: (order.get(i.priority, 9), i.received_at))

    def list_actions(self, status: Optional[ActionStatus] = None) -> list[Action]:
        return self._store.list_actions(status)

    def stats(self) -> dict:
        items = self._store.list_items()
        pending = self._store.list_actions(ActionStatus.PENDING)
        attention = self.attention_queue()
        return {
            "total_items": len(items),
            "needs_attention": len(attention),
            "pending_actions": len(pending),
            "auto_handled": len(items) - len(attention),
        }

    # ─── action lifecycle (human-in-the-loop) ─────────────────────────────────
    def approve_action(self, action_id: str,
                       edited_payload: Optional[dict] = None) -> Action:
        action = self._store.get_action(action_id)
        if action is None:
            raise KeyError(action_id)
        if action.status != ActionStatus.PENDING:
            raise ValueError(f"action is {action.status.value}, not pending")
        if edited_payload:
            action.payload.update(edited_payload)
        action.status = ActionStatus.APPROVED
        # execute via connector
        try:
            if not self._executor.can_execute(action):
                raise RuntimeError("no executor available for this action")
            action.result = self._executor.execute(action)
            action.status = ActionStatus.EXECUTED
        except Exception as exc:  # noqa: BLE001
            logger.exception("execution failed for %s", action_id)
            action.status = ActionStatus.FAILED
            action.result = str(exc)
        action.resolved_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        # learn from the approval
        self._memory.remember(
            f"Approved a {action.type.value} to {action.payload.get('to', 'someone')} "
            f"about '{action.payload.get('subject', action.title)}'.",
            kind="interaction")
        return action

    def reject_action(self, action_id: str) -> Action:
        action = self._store.get_action(action_id)
        if action is None:
            raise KeyError(action_id)
        action.status = ActionStatus.REJECTED
        action.resolved_at = datetime.now(timezone.utc)
        self._store.save_action(action)
        self._memory.remember(
            f"Vetoed a {action.type.value} about "
            f"'{action.payload.get('subject', action.title)}'. Learn from this.",
            kind="interaction")
        return action

    # ─── multi-step chat (Chief-of-Staff supervisor) ──────────────────────────
    def chat(self, message: str) -> Briefing:
        brief = self._supervisor.run(message)
        # persist any proposed actions as pending for approve/veto
        stored: list[Action] = []
        for action in brief.proposed_actions:
            stored.append(self._store.save_action(action))
        brief.proposed_actions = stored
        return brief

    # ─── proactive nudges ──────────────────────────────────────────────────────
    def generate_nudges(self) -> list[Action]:
        stale = self._nudges.find_stale(self._store.list_items())
        created: list[Action] = []
        existing = self._store.list_actions()
        for item in stale:
            if any(a.source_item_id == item.id and a.type == ActionType.SEND_NUDGE
                   for a in existing):
                continue
            created.append(self._store.save_action(self._nudges.draft_nudge(item)))
        logger.info("generate_nudges: %d drafted", len(created))
        return created

    # ─── memory ───────────────────────────────────────────────────────────────
    def list_memory(self):
        return self._memory.all()

    def remember(self, text: str, kind: str = "fact"):
        return self._memory.remember(text, kind=kind)


@lru_cache
def get_service() -> AideService:
    return AideService()
