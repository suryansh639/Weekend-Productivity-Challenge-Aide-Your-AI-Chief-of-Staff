"""End-to-end flow tests over the mock LLM + local store."""
from __future__ import annotations

from app.models import ActionStatus, ActionType, Priority


def test_seed_triages_and_surfaces_attention(service):
    inbox = service.list_inbox()
    assert len(inbox) == 10
    assert all(i.triaged for i in inbox)

    # the urgent outage + investor items should be surfaced for attention
    attention = service.attention_queue()
    subjects = " ".join(i.subject for i in attention).lower()
    assert "urgent" in subjects or "series a" in subjects
    # newsletters must NOT need a response
    news = next(i for i in inbox if "tldr" in i.sender.lower())
    assert news.needs_response is False
    assert news.priority == Priority.P3


def test_urgent_items_get_staged_draft_replies(service):
    pending = service.list_actions(ActionStatus.PENDING)
    replies = [a for a in pending if a.type == ActionType.SEND_REPLY]
    assert replies, "expected auto-staged draft replies for urgent items"
    assert all(a.payload.get("body") for a in replies)


def test_approve_executes_and_learns(service):
    reply = next(a for a in service.list_actions(ActionStatus.PENDING)
                 if a.type == ActionType.SEND_REPLY)
    before = len(service.list_memory())
    result = service.approve_action(reply.id)
    assert result.status == ActionStatus.EXECUTED
    assert result.result and "executed" in result.result
    # approving teaches Aide something (interaction memory grows)
    assert len(service.list_memory()) == before + 1


def test_reject_marks_rejected(service):
    action = service.list_actions(ActionStatus.PENDING)[0]
    result = service.reject_action(action.id)
    assert result.status == ActionStatus.REJECTED


def test_chat_produces_brief_and_pending_action(service):
    brief = service.chat("Prep me for the Series A follow-up and draft an email")
    assert brief.summary
    assert brief.talking_points
    pending = service.list_actions(ActionStatus.PENDING)
    assert any(a.type == ActionType.SEND_EMAIL for a in pending)


def test_nudges_flag_stale_thread(service):
    created = service.generate_nudges()
    assert created, "expected a nudge for the 5-day-old partnership thread"
    assert created[0].type == ActionType.SEND_NUDGE
    # idempotent — running again creates no duplicates
    assert service.generate_nudges() == []
