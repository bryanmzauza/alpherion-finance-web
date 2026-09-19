"""Engine assíncrona da API (usuário `api`: só leitura em `market`, statement_timeout 5 s)."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alpherion.settings import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().market_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
