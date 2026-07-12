"""Persistence interface. Agents/services depend on this, not on a concrete DB."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.models import Action, ActionStatus, InboxItem, MemoryRecord


class Store(ABC):
    # ─── inbox items ──────────────────────────────────────────────────────────
    @abstractmethod
    def upsert_item(self, item: InboxItem) -> InboxItem: ...

    @abstractmethod
    def get_item(self, item_id: str) -> Optional[InboxItem]: ...

    @abstractmethod
    def list_items(self) -> list[InboxItem]: ...

    # ─── actions ────────────────────────────────────────────────────────────────
    @abstractmethod
    def save_action(self, action: Action) -> Action: ...

    @abstractmethod
    def get_action(self, action_id: str) -> Optional[Action]: ...

    @abstractmethod
    def list_actions(self, status: Optional[ActionStatus] = None) -> list[Action]: ...

    # ─── memory ───────────────────────────────────────────────────────────────
    @abstractmethod
    def save_memory(self, record: MemoryRecord) -> MemoryRecord: ...

    @abstractmethod
    def list_memory(self) -> list[MemoryRecord]: ...

    # ─── maintenance ────────────────────────────────────────────────────────────
    @abstractmethod
    def reset(self) -> None:
        """Wipe all data (used by the seed script)."""
