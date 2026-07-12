"""Deterministic, offline mock LLM.

It inspects the prompt to detect which agent task is being asked and returns
realistic, structured output — so the whole product is demonstrable with zero
AWS credentials, and unit tests are fast and reproducible.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

_EMBED_DIM = 256


class MockLLM:
    provider = "mock"

    def complete(self, system: str, prompt: str, *, max_tokens: int = 1024,
                 temperature: float = 0.2) -> str:
        text = (system + "\n" + prompt).lower()
        if "schema: triageresult" in text:
            return json.dumps(self._triage(prompt))
        if "schema: briefing" in text:
            return json.dumps(self._briefing(prompt))
        if "schema: nudge" in text:
            return json.dumps(self._nudge(prompt))
        if "schema: reply" in text:
            return json.dumps(self._reply(prompt))
        return "OK"

    # ─── task handlers ────────────────────────────────────────────────────────
    def _triage(self, prompt: str) -> dict:
        subject, body, sender = _fields(prompt)
        blob = f"{subject} {body}".lower()
        urgent = any(k in blob for k in
                     ("urgent", "asap", "overdue", "outage", "down", "critical",
                      "today", "eod", "deadline"))
        exec_like = any(k in blob for k in
                        ("investor", "ceo", "board", "contract", "legal", "customer"))
        newsletter = any(k in blob for k in
                         ("newsletter", "unsubscribe", "digest", "weekly update", "promo"))
        if newsletter:
            priority, needs = "P3", False
        elif urgent and exec_like:
            priority, needs = "P0", True
        elif urgent:
            priority, needs = "P1", True
        elif exec_like:
            priority, needs = "P1", True
        else:
            needs = ("please" in blob) or ("can you" in blob) or ("could you" in blob)
            priority, needs = "P2", bool(needs)
        category = ("finance" if "invoice" in blob or "payment" in blob else
                    "sales" if "customer" in blob or "deal" in blob else
                    "meeting" if "meeting" in blob or "call" in blob or "calendar" in blob else
                    "newsletter" if newsletter else
                    "internal" if "team" in blob or "standup" in blob else "general")
        summary = _first_sentence(body) or subject or "No content."
        return {
            "priority": priority,
            "category": category,
            "needs_response": needs,
            "summary": summary[:200],
            "reasoning": f"Signals: urgent={urgent}, exec={exec_like}, "
                         f"newsletter={newsletter}. Sender {sender}.",
            "draft_reply": self._reply(prompt)["body"] if needs else "",
        }

    def _reply(self, prompt: str) -> dict:
        subject, body, sender = _fields(prompt)
        name = sender.split()[0] if sender else "there"
        return {
            "body": (
                f"Hi {name},\n\nThanks for the note on \"{subject or 'this'}\". "
                "I've reviewed it and will get back to you with specifics shortly. "
                "If it's time-sensitive, let me know and I'll prioritize.\n\nBest,\nYou"
            )
        }

    def _nudge(self, prompt: str) -> dict:
        subject, body, sender = _fields(prompt)
        name = sender.split()[0] if sender else "there"
        return {
            "body": (
                f"Hi {name},\n\nJust circling back on \"{subject or 'my last message'}\" "
                "— wanted to make sure this didn't slip through. Happy to jump on a "
                "quick call if that's easier.\n\nBest,\nYou"
            )
        }

    def _briefing(self, prompt: str) -> dict:
        request = _extract("request", prompt) or "your request"
        topic = re.sub(r"^(prep me for|prepare|brief me on)\s*", "",
                       request.strip(), flags=re.I)
        return {
            "summary": f"Here's your prep for {topic}. I pulled the most recent "
                       "related thread and your saved context, and drafted talking points.",
            "talking_points": [
                f"Lead with the headline outcome relevant to {topic}.",
                "Reference the last thread so it feels continuous, not cold.",
                "Have one concrete ask and one fallback ready.",
                "Close by proposing a specific next step + date.",
            ],
            "context_used": ["most recent related thread", "owner preferences", "prior notes"],
        }

    # ─── embeddings ─────────────────────────────────────────────────────────────
    def embed(self, text: str) -> list[float]:
        """Hash tokens into a fixed-dim bag-of-words vector, L2-normalized.

        Not semantically deep, but stable and good enough for demo-scale recall.
        """
        vec = [0.0] * _EMBED_DIM
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % _EMBED_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


# ─── prompt parsing helpers ───────────────────────────────────────────────────

def _extract(field: str, prompt: str) -> str:
    m = re.search(rf"{field}:\s*(.*)", prompt, flags=re.I)
    return m.group(1).strip() if m else ""


def _fields(prompt: str) -> tuple[str, str, str]:
    return _extract("subject", prompt), _extract("body", prompt), _extract("from", prompt)


def _first_sentence(text: str) -> str:
    text = text.strip().replace("\n", " ")
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return m.group(1) if m else text
