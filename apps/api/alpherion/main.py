"""Entrada da API: `uvicorn alpherion.main:app`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alpherion.db.session import get_engine
from alpherion.routers import health, internal, market, securities
from alpherion.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Falha cedo se o JSON de tokens estiver malformado (site.md §7.5).
    _ = get_settings().service_clients
    yield
    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Alpherion API",
        lifespan=lifespan,
        # Sem docs públicas em produção: a API é consumida só por serviços.
        docs_url="/docs" if settings.app_env == "dev" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env == "dev" else None,
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.include_router(health.router, prefix="/v1")
    app.include_router(securities.router, prefix="/v1")
    app.include_router(market.router, prefix="/v1")
    app.include_router(internal.router, prefix="/v1")
    return app


app = create_app()
