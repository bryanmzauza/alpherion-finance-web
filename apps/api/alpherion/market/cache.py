"""Cache das respostas de mercado (site.md §3.4).

Os TTLs não são um número redondo qualquer: cada um é o tempo em que o dado ainda é
verdade. Cotação e faixa do header, 5 minutos — é o que o §3.4 fixa. Página de ativo e
listas, até a próxima carga do pipeline, porque entre duas execuções do job o número
simplesmente não muda.

**Falha de cache nunca vira falha de resposta.** Se o Redis não responde, a rota busca
no banco e segue: o cache é otimização, e uma API que cai junto com o seu cache é uma
API com um ponto único de falha a mais.

A chave carrega o estado das flags do ADR-017. Sem isso, um cache aquecido enquanto a
licença estava ligada continuaria servindo preço depois de ela ser desligada.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any, Final

import redis.asyncio as redis_async
from pydantic import BaseModel

from alpherion.settings import get_settings

logger = logging.getLogger(__name__)

PREFIX: Final = "alpherion:market:"

#: TTL por família de resposta, em segundos.
TTL: Final[dict[str, int]] = {
    "quote": 300,  # cotação e faixa do header (§3.4)
    "strip": 300,
    "movers": 300,
    "security": 900,  # página de ativo: muda na carga do pipeline
    "list": 900,
    "events": 1800,  # agenda: muda uma vez por dia
    "reference": 3600,  # cadastro, setores, índices
}


@lru_cache
def get_client() -> redis_async.Redis:
    client: redis_async.Redis = redis_async.from_url(  # type: ignore[no-untyped-call]
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return client


def _flag_suffix() -> str:
    """Estado das travas do ADR-017 na chave: desligar a flag invalida o cache."""
    settings = get_settings()
    return f"b{int(settings.market_b3_prices_enabled)}c{int(settings.market_crypto_enabled)}"


def key(family: str, *parts: object) -> str:
    return PREFIX + ":".join([family, _flag_suffix(), *(str(part) for part in parts)])


def _encode(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    raise TypeError(f"não serializável: {type(value).__name__}")


async def cached[Model: BaseModel](
    family: str,
    *parts: object,
    model: type[Model],
    loader: Callable[[], Awaitable[Model]],
) -> Model:
    """Lê do cache ou chama `loader`. Qualquer erro de Redis é ignorado."""
    cache_key = key(family, *parts)
    client = get_client()
    try:
        raw = await client.get(cache_key)
        if raw:
            return model.model_validate_json(raw)
    except Exception as error:  # noqa: BLE001 — cache é otimização, não dependência
        logger.warning("cache indisponível na leitura de %s: %s", cache_key, error)

    value = await loader()
    try:
        await client.setex(cache_key, TTL.get(family, 300), value.model_dump_json())
    except Exception as error:  # noqa: BLE001
        logger.warning("cache indisponível na escrita de %s: %s", cache_key, error)
    return value


async def invalidate(family: str) -> int:
    """Apaga uma família inteira. Usado pelo runbook depois de uma correção de dado."""
    client = get_client()
    removed = 0
    try:
        async for found in client.scan_iter(match=f"{PREFIX}{family}:*", count=500):
            removed += await client.delete(found)
    except Exception as error:  # noqa: BLE001
        logger.warning("não foi possível invalidar %s: %s", family, error)
    return removed


def dumps(value: Any) -> str:
    """JSON com `Decimal` e datas — usado por respostas que não são modelos."""
    return json.dumps(value, default=_encode, ensure_ascii=False)
