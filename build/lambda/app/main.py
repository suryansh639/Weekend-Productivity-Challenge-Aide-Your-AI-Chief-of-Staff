"""FastAPI application + AWS Lambda handler (via Mangum)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import ActionDecision, ActionStatus, ChatRequest
from app.service import get_service

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title="Aide — AI Chief-of-Staff",
    version="0.1.0",
    description="Agentic inbox triage, multi-step prep, and proactive nudges — "
                "with a human approve/veto gate on every action.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm": settings.llm_provider, "store": settings.store_backend}


@app.get("/api/stats")
def stats() -> dict:
    return get_service().stats()


@app.post("/api/sync")
def sync() -> dict:
    return {"new_items": get_service().sync_inbox()}


@app.post("/api/seed")
def seed() -> dict:
    return get_service().seed_demo()


@app.get("/api/inbox")
def inbox() -> list:
    return get_service().list_inbox()


@app.get("/api/attention")
def attention() -> list:
    return get_service().attention_queue()


@app.get("/api/actions")
def actions(status: Optional[ActionStatus] = None) -> list:
    return get_service().list_actions(status)


@app.post("/api/actions/{action_id}/approve")
def approve(action_id: str, decision: Optional[ActionDecision] = None):
    try:
        edited = decision.edited_payload if decision else None
        return get_service().approve_action(action_id, edited)
    except KeyError:
        raise HTTPException(404, "action not found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post("/api/actions/{action_id}/reject")
def reject(action_id: str):
    try:
        return get_service().reject_action(action_id)
    except KeyError:
        raise HTTPException(404, "action not found")


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "message is required")
    return get_service().chat(req.message)


@app.post("/api/nudges/run")
def run_nudges() -> list:
    return get_service().generate_nudges()


@app.get("/api/memory")
def memory() -> list:
    return get_service().list_memory()


# ─── AWS Lambda entrypoint ────────────────────────────────────────────────────
try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:  # pragma: no cover - mangum absent in some local setups
    handler = None
