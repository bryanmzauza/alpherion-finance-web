from __future__ import annotations

import json
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from alpherion.settings import get_settings

WEB_TOKEN = "t" * 43
READONLY_TOKEN = "r" * 43
#: Cliente sem `market:read` — existe para provar que o escopo é exigido de verdade.
IMPORTS_TOKEN = "i" * 43

# Definido antes de qualquer `get_settings()`: os testes não leem o .env da raiz.
os.environ["API_SERVICE_TOKENS"] = json.dumps(
    {
        "web": {"token": WEB_TOKEN, "scopes": ["analyses:write", "market:read"]},
        "readonly": {"token": READONLY_TOKEN, "scopes": ["market:read"]},
        "imports": {"token": IMPORTS_TOKEN, "scopes": ["imports:write"]},
    }
)
os.environ["APP_ENV"] = "test"


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    get_settings.cache_clear()
    from alpherion.main import create_app

    with TestClient(create_app()) as c:
        yield c


class FakeRedisAsync:
    """Redis em memória, o bastante para o cache de mercado (`get`/`setex`).

    Sem isto, cada rota com cache tentaria abrir conexão de verdade e a suíte passaria
    a esperar o timeout do socket em todo teste. O caminho "Redis fora do ar" tem teste
    próprio em `test_market_cache.py`.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.hits = 0
        self.writes = 0

    async def get(self, key: str) -> str | None:
        value = self.store.get(key)
        if value is not None:
            self.hits += 1
        return value

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.writes += 1
        self.store[key] = value


@pytest.fixture(autouse=True)
def fake_cache(monkeypatch: pytest.MonkeyPatch) -> FakeRedisAsync:
    """Cache em memória, limpo a cada teste."""
    from alpherion.market import cache

    client = FakeRedisAsync()
    monkeypatch.setattr(cache, "get_client", lambda: client)
    return client
