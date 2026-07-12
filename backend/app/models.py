"""Domain models shared across the app (API contracts + persistence shapes)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Priority(str, Enum):
    P0 = "P0"  # drop everything
    P1 = "P1"  # today
    P2 = "P2"  # this week
    P3 = "P3"  # whenever / FYI


class Channel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    TASK = "task"


class ActionType(str, Enum):
    SEND_EMAIL = "send_email"
    SEND_REPLY = "send_reply"
    SCHEDULE_MEETING = "schedule_meeting"
    CREATE_TASK = "create_task"
    SEND_NUDGE = "send_nudge"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class InboxItem(BaseModel):
    """A normalized unit of incoming work from any connector."""

    id: str = Field(default_factory=lambda: _id("item"))
    channel: Channel
    thread_id: str
    sender: str
    sender_email: str = ""
    subject: str = ""
    body: str = ""
    received_at: datetime = Field(default_factory=_now)
    # populated by the triage agent
    triaged: bool = False
    priority: Optional[Priority] = None
    category: Optional[str] = None
    needs_response: Optional[bool] = None
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    # follow-up tracking (for proactive nudges)
    awaiting_reply_since: Optional[datetime] = None


class Action(BaseModel):
    """A side-effecting action proposed by an agent, gated by human approval."""

    id: str = Field(default_factory=lambda: _id("act"))
    type: ActionType
    status: ActionStatus = ActionStatus.PENDING
    title: str
    # free-form, action-specific payload (recipient, body, time, etc.)
    payload: dict = Field(default_factory=dict)
    rationale: str = ""
    source_item_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    resolved_at: Optional[datetime] = None
    result: Optional[str] = None


class MemoryRecord(BaseModel):
    """A durable fact/preference Aide has learned about its owner."""

    id: str = Field(default_factory=lambda: _id("mem"))
    kind: str  # "preference" | "contact" | "interaction" | "fact"
    text: str
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=_now)


class Briefing(BaseModel):
    """Output of the Chief-of-Staff supervisor for a multi-step request."""

    id: str = Field(default_factory=lambda: _id("brief"))
    request: str
    summary: str
    talking_points: list[str] = Field(default_factory=list)
    context_used: list[str] = Field(default_factory=list)
    proposed_actions: list[Action] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


# ─── API request/response models ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ActionDecision(BaseModel):
    edited_payload: Optional[dict] = None  # optional inline edits before approving
