"""Configuração da API e do worker, lida do `.env` na raiz do monorepo.

Toda variável nova entra também em `infra/env/.env.example`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> Path | None:
    """`.env` na raiz do monorepo (dev). Em container não existe: tudo vem do ambiente."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pnpm-workspace.yaml").exists():
            return parent / ".env"
    return None


SCOPES = frozenset({"analyses:write", "imports:write", "market:read", "quotes:read"})


class ServiceClient(BaseModel):
    """Um cliente da API (ex.: `web`, futuro `telegram-bot`) e seus escopos."""

    token: str = Field(min_length=32)
    scopes: frozenset[str]

    @field_validator("scopes")
    @classmethod
    def _known_scopes(cls, value: frozenset[str]) -> frozenset[str]:
        unknown = value - SCOPES
        if unknown:
            raise ValueError(f"escopos desconhecidos: {sorted(unknown)}")
        return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"

    # Banco: `api` só lê o schema market; `data` (worker) escreve e roda as migrations.
    market_database_url: str = "postgresql+psycopg://api@localhost:5432/alpherion"
    data_database_url: str = "postgresql+psycopg://data@localhost:5432/alpherion"
    redis_url: str = "redis://localhost:6379/0"

    # Auth por token de serviço (site.md §7.5): JSON {"web": {"token": "...", "scopes": [...]}}
    api_service_tokens: str = "{}"
    cors_origins: str = ""

    @property
    def service_clients(self) -> dict[str, ServiceClient]:
        raw = json.loads(self.api_service_tokens)
        return {name: ServiceClient(**cfg) for name, cfg in raw.items()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
