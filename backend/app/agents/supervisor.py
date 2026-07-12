"""Chief-of-Staff supervisor: turns a single free-form request into a multi-step
prep brief. This is a lightweight supervisor/worker graph — the supervisor plans,
delegates to retrieval workers (inbox search + semantic memory), composes a brief
with the LLM, and proposes (never auto-executes) follow-up actions.

The same shape maps cleanly onto LangGraph nodes with an ``interrupt`` before the
action step; here the human-in-the-loop gate lives in the service layer, which
persists proposed actions as ``pending`` for explicit approve/veto.
"""
from __future__ import annotations

import logging
import re

from app.agents.prompts import SUPERVISOR_SYSTEM
from app.llm.base import LLMClient, extract_json
from app.memory import MemoryService
from app.models import Action, ActionType, Briefing, InboxItem
from app.store.base import Store

logger = logging.getLogger("aide.supervisor")

_STOPWORDS = {"the", "a", "an", "for", "to", "me", "my", "on", "with", "and", "of",
              "prep", "prepare", "brief", "about", "in", "please", "help"}


class ChiefOfStaffSupervisor:
    def __init__(self, store: Store, memory: MemoryService, llm: LLMClient,
                 owner: str) -> None:
        self._store = store
        self._memory = memory
        self._llm = llm
        self._owner = owner
        self._system = SUPERVISOR_SYSTEM.format(owner=owner)

    def run(self, request: str) -> Briefing:
        # 1) plan → keyword terms from the request
        terms = self._keywords(request)
        # 2) worker: search the inbox for the most relevant thread
        related = self._search_inbox(terms)
        # 3) worker: semantic recall from memory
        memories = self._memory.recall(request, k=3)
        # 4) compose the brief
        context_block = self._build_context(related, memories)
        brief = self._compose(request, context_block)
        brief.context_used = (
            [f"thread: {i.subject}" for i in related[:2]]
            + [f"memory: {m.text}" for m in memories[:2]]
        )
        # 5) propose (not execute) a follow-up action when it makes sense
        brief.proposed_actions = self._propose_actions(request, related)
        return brief

    # ─── workers ────────────────────────────────────────────────────────────────
    def _keywords(self, request: str) -> set[str]:
        toks = re.findall(r"[a-zA-Z0-9]+", request.lower())
        return {t for t in toks if t not in _STOPWORDS and len(t) > 2}

    def _search_inbox(self, terms: set[str]) -> list[InboxItem]:
        scored: list[tuple[int, InboxItem]] = []
        for item in self._store.list_items():
            blob = f"{item.subject} {item.body} {item.sender}".lower()
            score = sum(1 for t in terms if t in blob)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda t: (t[0], t[1].received_at), reverse=True)
        return [i for _, i in scored[:3]]

    def _build_context(self, related: list[InboxItem],
                       memories: list) -> str:
        lines = ["RELATED THREADS:"]
        lines += [f"- {i.sender}: {i.subject} — {i.summary or i.body[:120]}"
                  for i in related] or ["- (none found)"]
        lines.append("\nKNOWN CONTEXT / PREFERENCES:")
        lines += [f"- {m.text}" for m in memories] or ["- (none yet)"]
        return "\n".join(lines)

    def _compose(self, request: str, context_block: str) -> Briefing:
        prompt = f"Request: {request}\n\nContext:\n{context_block}"
        try:
            data = extract_json(self._llm.complete(self._system, prompt, max_tokens=900))
        except Exception:  # noqa: BLE001
            logger.exception("briefing compose failed")
            data = {}
        return Briefing(
            request=request,
            summary=data.get("summary", "I couldn't fully assemble this brief."),
            talking_points=list(data.get("talking_points", [])),
        )

    def _propose_actions(self, request: str, related: list[InboxItem]) -> list[Action]:
        wants_followup = any(w in request.lower()
                             for w in ("follow up", "follow-up", "reply", "draft",
                                       "email", "send", "respond"))
        if not (wants_followup and related):
            return []
        target = related[0]
        return [Action(
            type=ActionType.SEND_EMAIL,
            title=f"Draft follow-up to {target.sender}",
            payload={
                "to": target.sender_email,
                "subject": f"Re: {target.subject}",
                "body": f"Hi {target.sender.split()[0]},\n\nFollowing up on "
                        f"\"{target.subject}\". [Aide drafted this from your request: "
                        f"\"{request}\".]\n\nBest,\n{self._owner}",
            },
            rationale=f"Your request implied a follow-up on the '{target.subject}' thread.",
            source_item_id=target.id,
        )]
