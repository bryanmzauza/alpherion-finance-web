"""Engine e sessão assíncronas da API (usuário `api`: só leitura em `market`).

`statement_timeout` de 5 s vem do próprio usuário no Postgres (`init.sql`, §7.6), não
daqui: assim vale para qualquer conexão, inclusive um `psql` de investigação.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alpherion.settings import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().market_database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependência das rotas. A API só lê: nenhum `commit` acontece aqui."""
    async with get_sessionmaker()() as session:
        yield session
