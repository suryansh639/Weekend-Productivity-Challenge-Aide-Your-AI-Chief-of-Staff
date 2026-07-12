"""DynamoDB single-table store for production.

Design: PK = entity type ("ITEM" | "ACTION" | "MEM"), SK = entity id.
The full record is stored as a JSON string in ``doc`` — this keeps float
embeddings intact (no Decimal juggling) and keeps the table schema-flexible.
Listing is a ``Query`` on the partition; at personal-assistant scale this is
cheap and stays comfortably inside the DynamoDB Free Tier.
"""
from __future__ import annotations

import json
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

from app.models import Action, ActionStatus, InboxItem, MemoryRecord
from app.store.base import Store

_ITEM, _ACTION, _MEM = "ITEM", "ACTION", "MEM"


class DynamoStore(Store):
    def __init__(self, table_name: str, region: str) -> None:
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def _put(self, pk: str, sk: str, model) -> None:
        self._table.put_item(Item={"pk": pk, "sk": sk, "doc": model.model_dump_json()})

    def _query(self, pk: str) -> list[dict]:
        out: list[dict] = []
        kwargs = {"KeyConditionExpression": Key("pk").eq(pk)}
        while True:
            resp = self._table.query(**kwargs)
            out.extend(json.loads(i["doc"]) for i in resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                return out
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    def _get(self, pk: str, sk: str) -> Optional[dict]:
        resp = self._table.get_item(Key={"pk": pk, "sk": sk})
        item = resp.get("Item")
        return json.loads(item["doc"]) if item else None

    # ─── items ────────────────────────────────────────────────────────────────
    def upsert_item(self, item: InboxItem) -> InboxItem:
        self._put(_ITEM, item.id, item)
        return item

    def get_item(self, item_id: str) -> Optional[InboxItem]:
        raw = self._get(_ITEM, item_id)
        return InboxItem(**raw) if raw else None

    def list_items(self) -> list[InboxItem]:
        items = [InboxItem(**r) for r in self._query(_ITEM)]
        return sorted(items, key=lambda i: i.received_at, reverse=True)

    # ─── actions ────────────────────────────────────────────────────────────────
    def save_action(self, action: Action) -> Action:
        self._put(_ACTION, action.id, action)
        return action

    def get_action(self, action_id: str) -> Optional[Action]:
        raw = self._get(_ACTION, action_id)
        return Action(**raw) if raw else None

    def list_actions(self, status: Optional[ActionStatus] = None) -> list[Action]:
        actions = [Action(**r) for r in self._query(_ACTION)]
        if status is not None:
            actions = [a for a in actions if a.status == status]
        return sorted(actions, key=lambda a: a.created_at, reverse=True)

    # ─── memory ───────────────────────────────────────────────────────────────
    def save_memory(self, record: MemoryRecord) -> MemoryRecord:
        self._put(_MEM, record.id, record)
        return record

    def list_memory(self) -> list[MemoryRecord]:
        return [MemoryRecord(**r) for r in self._query(_MEM)]

    def reset(self) -> None:
        for pk in (_ITEM, _ACTION, _MEM):
            resp = self._table.query(KeyConditionExpression=Key("pk").eq(pk))
            with self._table.batch_writer() as batch:
                for it in resp.get("Items", []):
                    batch.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})
