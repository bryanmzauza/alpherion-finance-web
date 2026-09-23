"""CoinGecko — preços e dados de criptoativos.

**Só desenvolvimento** (ADR-017). O plano Demo do CoinGecko não permite uso comercial, e
`docs/fontes-de-dados.md` registra a fonte **sem** `terms_checked_at`: em produção o job
não roda e `MARKET_CRYPTO_ENABLED` fica `false`, com as páginas de cripto mostrando "—"
e o motivo. Trocar para o plano Analyst ou para uma exchange muda só este arquivo — é
para isso que a leitura está isolada aqui.

A API é documentada e estável, ao contrário da B3; o cuidado aqui é outro: **limite de
requisições**. O plano gratuito derruba a chamada com 429 em rajada, então o job pede
uma página por vez e o worker espaça as chamadas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

import httpx

from alpherion.data.sources.http import DEFAULT_TIMEOUT, USER_AGENT, SourceError, check_host

logger = logging.getLogger(__name__)

BASE_URL: Final = "https://api.coingecko.com/api/v3"
CURRENCY: Final = "brl"
#: 250 é o máximo por página da API.
PAGE_SIZE: Final = 250


@dataclass(frozen=True, slots=True)
class CryptoAssetRow:
    """Um criptoativo com a cotação do momento, pronto para `crypto_assets`/`crypto_daily`."""

    asset_id: str
    symbol: str
    name: str
    price: Decimal | None
    market_cap: Decimal | None
    volume_24h: Decimal | None
    change_24h: Decimal | None
    circulating_supply: Decimal | None
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class CryptoPoint:
    """Um ponto do histórico diário."""

    asset_id: str
    date: date
    price: Decimal
    market_cap: Decimal | None
    volume: Decimal | None


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _percent_points(value: Any) -> Decimal | None:
    parsed = _decimal(value)
    return None if parsed is None else parsed / 100


def _get(path: str, params: dict[str, Any], http: httpx.Client | None) -> Any:
    url = f"{BASE_URL}/{path.lstrip('/')}"
    check_host(url)

    def _call(session: httpx.Client) -> httpx.Response:
        return session.get(url, params=params)

    if http is not None:
        response = _call(http)
    else:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT}) as session:
            response = _call(session)

    if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
        raise SourceError("CoinGecko: limite de requisições (429) — espaçar o job")
    if response.status_code != httpx.codes.OK:
        raise SourceError(f"CoinGecko {path}: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as error:
        raise SourceError(f"CoinGecko {path}: resposta não é JSON") from error


def fetch_markets(
    *,
    page: int = 1,
    per_page: int = PAGE_SIZE,
    http: httpx.Client | None = None,
) -> list[CryptoAssetRow]:
    """Lista por valor de mercado, com a cotação em reais."""
    payload = _get(
        "coins/markets",
        {
            "vs_currency": CURRENCY,
            "order": "market_cap_desc",
            "per_page": min(per_page, PAGE_SIZE),
            "page": page,
            "sparkline": "false",
        },
        http,
    )
    if not isinstance(payload, list):
        raise SourceError("CoinGecko: formato inesperado em coins/markets")
    assets = [row for item in payload if (row := _parse_market(item)) is not None]
    logger.info("CoinGecko: %d criptoativos na página %d", len(assets), page)
    return assets


def _parse_market(item: Any) -> CryptoAssetRow | None:
    if not isinstance(item, dict) or not item.get("id"):
        return None
    return CryptoAssetRow(
        asset_id=str(item["id"]),
        symbol=str(item.get("symbol", "")).upper()[:20],
        name=str(item.get("name", ""))[:120],
        price=_decimal(item.get("current_price")),
        market_cap=_decimal(item.get("market_cap")),
        volume_24h=_decimal(item.get("total_volume")),
        # A CoinGecko manda em pontos percentuais (-1.25 = -1,25%); a coluna é `Ratio`
        # (fração), como toda variação do produto — e é fração que o `web` formata.
        change_24h=_percent_points(item.get("price_change_percentage_24h")),
        circulating_supply=_decimal(item.get("circulating_supply")),
        updated_at=_parse_timestamp(item.get("last_updated")),
    )


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_history(
    asset_id: str,
    *,
    days: int = 365,
    http: httpx.Client | None = None,
) -> list[CryptoPoint]:
    """Histórico diário de um ativo.

    O CoinGecko devolve três séries paralelas (preço, valor de mercado, volume) com
    carimbo em milissegundos. Juntamos por dia; dia sem preço não vira ponto — a série
    do gráfico não pode ter buraco preenchido com zero.
    """
    payload = _get(
        f"coins/{asset_id}/market_chart",
        {"vs_currency": CURRENCY, "days": days, "interval": "daily"},
        http,
    )
    if not isinstance(payload, dict):
        raise SourceError(f"CoinGecko: formato inesperado no histórico de {asset_id}")

    prices = _by_day(payload.get("prices"))
    caps = _by_day(payload.get("market_caps"))
    volumes = _by_day(payload.get("total_volumes"))
    points = [
        CryptoPoint(
            asset_id=asset_id,
            date=day,
            price=price,
            market_cap=caps.get(day),
            volume=volumes.get(day),
        )
        for day, price in sorted(prices.items())
    ]
    logger.info("CoinGecko: %d pontos de histórico de %s", len(points), asset_id)
    return points


def _by_day(series: Any) -> dict[date, Decimal]:
    """`[[1695168000000, 123.45], …]` → {data: valor}, último valor do dia."""
    result: dict[date, Decimal] = {}
    if not isinstance(series, list):
        return result
    for item in series:
        if not isinstance(item, list) or len(item) < 2:
            continue
        value = _decimal(item[1])
        if value is None:
            continue
        try:
            day = datetime.fromtimestamp(float(item[0]) / 1000, tz=UTC).date()
        except (ValueError, OSError, TypeError):
            continue
        result[day] = value
    return result
