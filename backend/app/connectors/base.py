"""Connector interfaces.

A ``SourceConnector`` pulls normalized inbox items from an external system
(Gmail, Slack, Linear...). An ``ActionExecutor`` performs an approved action in
that system. Adding a real integration = implementing these two protocols; no
agent code changes.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models import Action, InboxItem


@runtime_checkable
class SourceConnector(Protocol):
    name: str

    def fetch(self) -> list[InboxItem]:
        """Return newly observed inbox items."""
        ...


@runtime_checkable
class ActionExecutor(Protocol):
    def can_execute(self, action: Action) -> bool: ...

    def execute(self, action: Action) -> str:
        """Perform the side effect and return a human-readable result string."""
        ...
