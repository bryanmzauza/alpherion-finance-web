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
