from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_health_is_public_and_hides_versions(client: TestClient) -> None:
    with (
        patch("alpherion.routers.health._check_db", AsyncMock(return_value="ok")),
        patch("alpherion.routers.health._check_redis", AsyncMock(return_value="ok")),
    ):
        res = client.get("/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "checks": {"db": "ok", "redis": "ok"}}
    assert "version" not in res.text.lower()


def test_health_reports_503_when_a_dependency_fails(client: TestClient) -> None:
    with (
        patch("alpherion.routers.health._check_db", AsyncMock(return_value="fail")),
        patch("alpherion.routers.health._check_redis", AsyncMock(return_value="ok")),
    ):
        res = client.get("/v1/health")
    assert res.status_code == 503
    assert res.json()["status"] == "degraded"
    assert res.json()["checks"]["db"] == "fail"
