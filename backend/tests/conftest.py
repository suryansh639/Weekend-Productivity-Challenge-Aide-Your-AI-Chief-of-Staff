"""Test fixtures: force offline providers and an isolated temp store per test."""
from __future__ import annotations

import pytest


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setenv("AIDE_LLM_PROVIDER", "mock")
    monkeypatch.setenv("AIDE_STORE_BACKEND", "local")
    monkeypatch.setenv("AIDE_LOCAL_DB_PATH", str(tmp_path / "db.json"))
    monkeypatch.setenv("AIDE_OWNER_NAME", "You")

    # rebuild the cached singletons against the fresh env
    from app import config
    from app.llm import factory as llm_factory
    from app import service as service_mod
    from app.store import factory as store_factory

    config.get_settings.cache_clear()
    llm_factory.get_llm.cache_clear()
    store_factory.get_store.cache_clear()
    service_mod.get_service.cache_clear()

    svc = service_mod.AideService()
    svc.seed_demo()
    return svc
