"""Demo connector: a realistic, seeded inbox so the product works end-to-end
without any OAuth. Execution is simulated (logged) rather than actually sending.

Swap this for GmailConnector (see gmail.py) to go live.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.models import Action, Channel, InboxItem

logger = logging.getLogger("aide.demo")


def _ago(days: float = 0, hours: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)


def _seed_items() -> list[InboxItem]:
    return [
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-invest",
            sender="Dana Reyes", sender_email="dana@northstar.vc",
            subject="Re: Series A — follow-ups before Thursday",
            body="Hi — great chatting today. Before our call Thursday, can you send "
                 "the updated deck and the latest ARR numbers? Also curious how you're "
                 "thinking about the go-to-market hire. Talk soon.",
            received_at=_ago(hours=2)),
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-outage",
            sender="PagerDuty", sender_email="alerts@pagerduty.com",
            subject="URGENT: API error rate above threshold (prod)",
            body="Error rate on the payments API crossed 5% for 10 minutes. This is "
                 "critical and affecting customers right now. Ack required.",
            received_at=_ago(hours=1)),
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-invoice",
            sender="Acme Billing", sender_email="billing@acme.com",
            subject="Invoice #4471 is overdue",
            body="Your payment for invoice #4471 ($4,200) is 6 days overdue. Please "
                 "remit payment to avoid a service interruption.",
            received_at=_ago(days=1)),
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-customer",
            sender="Priya Menon", sender_email="priya@bigco.com",
            subject="Can you help us with the SSO rollout?",
            body="We're a customer on the growth plan. Can you help us configure SAML "
                 "SSO this week? We have a security review coming up.",
            received_at=_ago(days=1, hours=3)),
        InboxItem(
            channel=Channel.SLACK, thread_id="t-standup",
            sender="Eng Team", sender_email="eng@internal",
            subject="Daily standup thread",
            body="Reminder: post your standup update in this thread by 10am.",
            received_at=_ago(hours=5)),
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-news",
            sender="TLDR Newsletter", sender_email="digest@tldr.tech",
            subject="TLDR: today's tech news digest",
            body="The biggest stories in tech today. Unsubscribe anytime.",
            received_at=_ago(hours=6)),
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-legal",
            sender="Sam Cho", sender_email="sam@lawfirm.com",
            subject="Contract redlines for your review",
            body="Attached are the redlines on the vendor contract. Please review the "
                 "liability section — we need your sign-off before Friday.",
            received_at=_ago(days=2)),
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-coffee",
            sender="Jordan Lee", sender_email="jordan@friend.com",
            subject="Coffee next week?",
            body="Been a while! Want to grab coffee sometime next week? No rush.",
            received_at=_ago(days=2, hours=4)),
        # A thread the owner sent and is awaiting a reply on — fuel for nudges.
        InboxItem(
            channel=Channel.EMAIL, thread_id="t-partner",
            sender="You", sender_email="you@example.com",
            subject="Partnership proposal — next steps",
            body="Hi Alex, following up on our chat — sharing the proposal here. Let me "
                 "know if the scope looks right and we can move to a pilot.",
            received_at=_ago(days=5),
            awaiting_reply_since=_ago(days=5)),
        InboxItem(
            channel=Channel.TASK, thread_id="t-task",
            sender="Linear", sender_email="notifications@linear.app",
            subject="You were assigned: Finalize Q3 hiring plan",
            body="Due in 2 days. Ping the hiring manager and finalize the headcount.",
            received_at=_ago(days=1)),
    ]


class DemoConnector:
    name = "demo"

    def fetch(self) -> list[InboxItem]:
        return _seed_items()


class DemoExecutor:
    """Simulates executing an approved action (logs it, returns a receipt)."""

    def can_execute(self, action: Action) -> bool:
        return True

    def execute(self, action: Action) -> str:
        logger.info("EXECUTE %s: %s | payload=%s",
                    action.type.value, action.title, action.payload)
        target = action.payload.get("to") or action.payload.get("when") or "system"
        return f"[demo] {action.type.value} executed → {target}"
