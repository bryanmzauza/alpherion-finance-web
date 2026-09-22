"""Cache das respostas de mercado.

Três comportamentos que o cache precisa ter, e que não são óbvios:

1. **Redis fora do ar não derruba a resposta.** Cache é otimização; uma API que cai
   junto com o seu cache tem um ponto único de falha a mais.
2. **A chave carrega o estado das flags do ADR-017.** Sem isso, um cache aquecido
   enquanto a licença estava ligada continuaria servindo preço depois de ela ser
   desligada — a trava seria contornável por acidente.
3. **O que volta do cache é igual ao que foi servido.** Serializar e reler não pode
   perder `Decimal`, data nem o bloco de fonte.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from alpherion.market import cache, schemas

from .conftest import FakeRedisAsync

ITEM = schemas.StripItem(
    source=schemas.SourceRef(
        source="b3",
        attribution="Fonte: B3",
        document="fechamento de 18/09/2026",
        updated_at=dt.datetime(2026, 9, 18, 20, 0, tzinfo=dt.UTC),
    ),
    key="ibovespa",
    label="Ibovespa",
    value=Decimal("142500.75"),
    unit="pts",
)


class RedisQuebrado:
    async def get(self, _key: str) -> str | None:
        raise ConnectionError("redis fora do ar")

    async def setex(self, _key: str, _ttl: int, _value: str) -> None:
        raise ConnectionError("redis fora do ar")


async def test_redis_fora_do_ar_nao_derruba_a_resposta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache, "get_client", RedisQuebrado)

    async def loader() -> schemas.StripItem:
        return ITEM

    resultado = await cache.cached("strip", "x", model=schemas.StripItem, loader=loader)
    assert resultado.value == ITEM.value


async def test_segunda_chamada_vem_do_cache(fake_cache: FakeRedisAsync) -> None:
    chamadas = 0

    async def loader() -> schemas.StripItem:
        nonlocal chamadas
        chamadas += 1
        return ITEM

    primeiro = await cache.cached("strip", "ibov", model=schemas.StripItem, loader=loader)
    segundo = await cache.cached("strip", "ibov", model=schemas.StripItem, loader=loader)

    assert chamadas == 1
    assert fake_cache.hits == 1
    assert segundo == primeiro, "ida e volta pelo JSON não pode perder Decimal nem data"
    assert segundo.value == Decimal("142500.75")
    assert segundo.source.updated_at == ITEM.source.updated_at


async def test_lista_tambem_e_cacheada(fake_cache: FakeRedisAsync) -> None:
    async def loader() -> list[schemas.StripItem]:
        return [ITEM]

    await cache.cached_list("strip", model=schemas.StripItem, loader=loader)
    itens = await cache.cached_list("strip", model=schemas.StripItem, loader=loader)

    assert fake_cache.hits == 1
    assert itens[0].label == "Ibovespa"


def test_chave_muda_quando_a_licenca_muda(monkeypatch: pytest.MonkeyPatch) -> None:
    """Desligar a flag invalida o cache: a trava do ADR-017 não pode ser contornável."""
    from alpherion.settings import Settings

    def com(prices: bool, crypto: bool) -> str:
        monkeypatch.setattr(
            cache,
            "get_settings",
            lambda: Settings(market_b3_prices_enabled=prices, market_crypto_enabled=crypto),
        )
        return cache.key("strip", "ibovespa")

    travado = com(False, False)
    liberado = com(True, False)
    so_cripto = com(False, True)

    assert len({travado, liberado, so_cripto}) == 3


def test_ttl_da_cotacao_e_de_cinco_minutos() -> None:
    """§3.4 fixa 5 min para cotação, faixa e listas do dia."""
    assert cache.TTL["quote"] == 300
    assert cache.TTL["strip"] == 300
    assert cache.TTL["movers"] == 300


def test_toda_familia_usada_tem_ttl_declarado() -> None:
    assert set(cache.TTL) >= {"quote", "strip", "movers", "security", "list", "events", "reference"}


def test_chave_sempre_tem_prefixo_do_projeto() -> None:
    """O Redis é compartilhado com rate limit e locks: prefixo evita colisão."""
    assert cache.key("strip", "x").startswith(cache.PREFIX)


def test_encode_de_tipos_do_dominio() -> None:
    assert cache.dumps({"v": Decimal("1.5")}) == '{"v": "1.5"}'
    assert cache.dumps({"d": dt.date(2026, 9, 18)}) == '{"d": "2026-09-18"}'
    with pytest.raises(TypeError):
        cache.dumps({"x": object()})
