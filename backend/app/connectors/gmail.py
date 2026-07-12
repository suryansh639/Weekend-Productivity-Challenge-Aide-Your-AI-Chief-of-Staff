"""Gmail connector — the production integration point (intentionally a stub).

Wiring this up is the same shape as the DemoConnector: implement ``fetch`` to
pull messages via the Gmail API, and an executor whose ``execute`` sends mail via
``users.messages.send``. OAuth tokens are expected in Secrets Manager.

Left as a clearly-marked stub so the challenge build stays deployable and
demoable without live Google OAuth credentials.
"""
from __future__ import annotations

from app.models import Action, InboxItem


class GmailConnector:
    name = "gmail"

    def __init__(self, oauth_token: str | None = None) -> None:
        self._token = oauth_token

    def fetch(self) -> list[InboxItem]:  # pragma: no cover - integration stub
        raise NotImplementedError(
            "Provide Google OAuth credentials and implement Gmail API fetch. "
            "Use the DemoConnector for local/demo runs."
        )


class GmailExecutor:  # pragma: no cover - integration stub
    def can_execute(self, action: Action) -> bool:
        return False

    def execute(self, action: Action) -> str:
        raise NotImplementedError("Implement users.messages.send with OAuth token.")
