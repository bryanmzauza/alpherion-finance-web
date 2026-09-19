from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from alpherion.auth import Caller, require_scopes
from alpherion.settings import get_settings
from tests.conftest import READONLY_TOKEN, WEB_TOKEN

Writer = Annotated[Caller, Depends(require_scopes("analyses:write"))]
Reader = Annotated[Caller, Depends(require_scopes("market:read"))]


@pytest.fixture(scope="module")
def protected() -> TestClient:
    get_settings.cache_clear()
    app = FastAPI()

    @app.get("/write")
    def write(caller: Writer) -> dict[str, str]:
        return {"caller": caller.name}

    @app.get("/read")
    def read(caller: Reader) -> dict[str, str]:
        return {"caller": caller.name}

    return TestClient(app)


def test_missing_token_is_401(protected: TestClient) -> None:
    res = protected.get("/read")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_wrong_token_is_401(protected: TestClient) -> None:
    res = protected.get("/read", headers={"Authorization": "Bearer " + "x" * 43})
    assert res.status_code == 401


def test_wrong_scheme_is_401(protected: TestClient) -> None:
    res = protected.get("/read", headers={"Authorization": f"Basic {WEB_TOKEN}"})
    assert res.status_code == 401


def test_token_without_scope_is_403(protected: TestClient) -> None:
    res = protected.get("/write", headers={"Authorization": f"Bearer {READONLY_TOKEN}"})
    assert res.status_code == 403
    assert "analyses:write" in res.json()["detail"]


def test_token_with_scope_identifies_caller(protected: TestClient) -> None:
    res = protected.get("/write", headers={"Authorization": f"Bearer {WEB_TOKEN}"})
    assert res.status_code == 200
    assert res.json() == {"caller": "web"}
    res = protected.get("/read", headers={"Authorization": f"Bearer {READONLY_TOKEN}"})
    assert res.json() == {"caller": "readonly"}
