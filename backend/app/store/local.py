"""Local JSON-file store for offline development and demos."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from app.models import Action, ActionStatus, InboxItem, MemoryRecord
from app.store.base import Store


class LocalStore(Store):
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._data: dict[str, dict] = {"items": {}, "actions": {}, "memory": {}}
        self._load()

    # ─── persistence ────────────────────────────────────────────────────────────
    def _load(self) -> None:
        if self._path.exists():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
            for bucket in ("items", "actions", "memory"):
                self._data.setdefault(bucket, {})

    def _flush(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, default=str), encoding="utf-8"
        )

    # ─── items ────────────────────────────────────────────────────────────────
    def upsert_item(self, item: InboxItem) -> InboxItem:
        with self._lock:
            self._data["items"][item.id] = item.model_dump(mode="json")
            self._flush()
        return item

    def get_item(self, item_id: str) -> Optional[InboxItem]:
        raw = self._data["items"].get(item_id)
        return InboxItem(**raw) if raw else None

    def list_items(self) -> list[InboxItem]:
        items = [InboxItem(**raw) for raw in self._data["items"].values()]
        return sorted(items, key=lambda i: i.received_at, reverse=True)

    # ─── actions ────────────────────────────────────────────────────────────────
    def save_action(self, action: Action) -> Action:
        with self._lock:
            self._data["actions"][action.id] = action.model_dump(mode="json")
            self._flush()
        return action

    def get_action(self, action_id: str) -> Optional[Action]:
        raw = self._data["actions"].get(action_id)
        return Action(**raw) if raw else None

    def list_actions(self, status: Optional[ActionStatus] = None) -> list[Action]:
        actions = [Action(**raw) for raw in self._data["actions"].values()]
        if status is not None:
            actions = [a for a in actions if a.status == status]
        return sorted(actions, key=lambda a: a.created_at, reverse=True)

    # ─── memory ───────────────────────────────────────────────────────────────
    def save_memory(self, record: MemoryRecord) -> MemoryRecord:
        with self._lock:
            self._data["memory"][record.id] = record.model_dump(mode="json")
            self._flush()
        return record

    def list_memory(self) -> list[MemoryRecord]:
        return [MemoryRecord(**raw) for raw in self._data["memory"].values()]

    def reset(self) -> None:
        with self._lock:
            self._data = {"items": {}, "actions": {}, "memory": {}}
            self._flush()
