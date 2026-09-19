"""`GET /v1/health` — público, sem versão (site.md §7.5). Usado pelo Uptime Kuma e pelo deploy."""

from __future__ import annotations

from typing import Annotated, Literal

import redis.asyncio as redis_async
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alpherion.db.session import get_engine
from alpherion.settings import Settings, get_settings

router = APIRouter(tags=["health"])

Check = Literal["ok", "fail"]


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, Check]


async def _check_db(engine: AsyncEngine) -> Check:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:  # noqa: BLE001 — o motivo vai para o log, não para a resposta
        return "fail"


async def _check_redis(url: str) -> Check:
    client: redis_async.Redis = redis_async.from_url(  # type: ignore[no-untyped-call]
        url, socket_connect_timeout=2, socket_timeout=2
    )
    try:
        await client.ping()
        return "ok"
    except Exception:  # noqa: BLE001
        return "fail"
    finally:
        await client.aclose()


@router.get("/health", response_model=Health)
async def health(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> Health:
    checks: dict[str, Check] = {
        "db": await _check_db(engine),
        "redis": await _check_redis(settings.redis_url),
    }
    ok = all(v == "ok" for v in checks.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Health(status="ok" if ok else "degraded", checks=checks)
