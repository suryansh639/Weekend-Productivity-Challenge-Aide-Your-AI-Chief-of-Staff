"""Scheduled Lambda: proactively draft nudges for stale threads.

Triggered by EventBridge Scheduler (see infra/template.yaml). Drafted nudges are
staged as *pending* actions — the owner still approves/vetoes each one.
"""
from __future__ import annotations

import json
import logging

from app.service import get_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aide.lambda.nudge")


def handler(event, context):  # noqa: ANN001 - Lambda signature
    # Optionally sync first so we're reasoning over the latest inbox.
    service = get_service()
    service.sync_inbox()
    created = service.generate_nudges()
    logger.info("drafted %d nudges", len(created))
    return {
        "statusCode": 200,
        "body": json.dumps({"drafted": len(created),
                            "actions": [a.id for a in created]}),
    }
