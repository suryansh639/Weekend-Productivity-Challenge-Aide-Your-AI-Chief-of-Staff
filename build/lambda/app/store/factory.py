"""Select the store backend based on configuration."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.store.base import Store


@lru_cache
def get_store() -> Store:
    settings = get_settings()
    if settings.store_backend == "dynamo":
        from app.store.dynamo import DynamoStore

        return DynamoStore(settings.dynamo_table, settings.aws_region)
    from app.store.local import LocalStore

    return LocalStore(settings.local_db_path)
