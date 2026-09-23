"""Valorização da carteira (`POST /v1/portfolios/valuation`, site.md §2.3).

Recebe posições já derivadas pelo `web` (quantidade, preço médio) e devolve preço atual,
valor, resultado e peso por ativo, e os totais. A API não guarda nada disso.

Três regras:

- **Preço vem de fonte oficial**: último fechamento do COTAHIST (B3), preço em reais do
  CoinGecko, PU de venda (resgate) do Tesouro Transparente.
- **A trava do ADR-017 vale aqui também**: sem licença, a posição da B3 ou de cripto sai
  com preço e valor `null` **e o motivo** — nunca zero, nunca um preço "estimado".
- **Peso é sobre o que tem valor.** Posição sem preço fica fora do denominador e o total
  sai marcado como parcial; senão o peso de tudo o mais estaria errado sem aviso.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.db.models import CryptoDaily, DailyQuote, TreasuryDaily
from alpherion.importers.models import AssetClass, MarketRef
from alpherion.market.flags import CRYPTO_REASON, PRICE_REASON, Gate

MAX_POSITIONS: Final = 100
#: Preço mais velho que isto é tratado como ausente (papel suspenso, título vencido).
STALE_AFTER_DAYS: Final = 45
CENT: Final = Decimal("0.01")
RATIO: Final = Decimal("0.000001")

SOURCES: Final[dict[str, str]] = {
    "ticker": "Fonte: B3 (COTAHIST)",
    "coingecko_id": "Fonte: CoinGecko",
    "treasury_slug": "Fonte: Tesouro Transparente",
}


class ValuationPosition(BaseModel):
    symbol: str = Field(min_length=1, max_length=80)
    market_ref: MarketRef
    asset_class: AssetClass
    quantity: Decimal | None = Field(default=None, gt=0)
    avg_price: Decimal | None = Field(default=None, ge=0)
    value_brl: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _quantity_or_value(self) -> ValuationPosition:
        if (self.quantity is None) == (self.value_brl is None):
            raise ValueError("informe quantidade ou valor em reais (um dos dois)")
        return self


class ValuationRequest(BaseModel):
    positions: list[ValuationPosition] = Field(max_length=MAX_POSITIONS)


class ValuedPosition(BaseModel):
    symbol: str
    market_ref: MarketRef
    asset_class: AssetClass
    quantity: Decimal | None
    avg_price: Decimal | None
    cost: Decimal | None
    price: Decimal | None
    price_date: dt.date | None
    value: Decimal | None
    result: Decimal | None
    result_percent: Decimal | None
    weight: Decimal | None
    #: "Fonte: B3 (COTAHIST)" — o `SourceBadge` da linha. `None` para posição por valor.
    source: str | None
    missing_reasons: dict[str, str] = Field(default_factory=dict)


class Valuation(BaseModel):
    positions: list[ValuedPosition]
    total_value: Decimal
    total_cost: Decimal | None
    total_result: Decimal | None
    #: `True` quando alguma posição ficou sem valor (fora do total e dos pesos) ou sem
    #: resultado (fora de `total_cost`/`total_result`).
    partial: bool
    as_of: dt.date | None


@dataclass(frozen=True, slots=True)
class Quote:
    price: Decimal
    date: dt.date


class PriceSource(Protocol):
    async def quotes(self, tickers: set[str]) -> Mapping[str, Quote]: ...
    async def crypto(self, ids: set[str]) -> Mapping[str, Quote]: ...
    async def treasury(self, slugs: set[str]) -> Mapping[str, Quote]: ...


class DbPriceSource:
    """Último preço de cada ativo, uma consulta por fonte (`DISTINCT ON`)."""

    def __init__(self, session: AsyncSession, today: dt.date) -> None:
        self.session = session
        self.since = today - dt.timedelta(days=STALE_AFTER_DAYS)

    async def quotes(self, tickers: set[str]) -> Mapping[str, Quote]:
        if not tickers:
            return {}
        rows = await self.session.execute(
            select(DailyQuote.ticker, DailyQuote.date, DailyQuote.close)
            .where(DailyQuote.ticker.in_(tickers), DailyQuote.date >= self.since)
            .distinct(DailyQuote.ticker)
            .order_by(DailyQuote.ticker, DailyQuote.date.desc())
        )
        return {t: Quote(price=c, date=d) for t, d, c in rows}

    async def crypto(self, ids: set[str]) -> Mapping[str, Quote]:
        if not ids:
            return {}
        rows = await self.session.execute(
            select(CryptoDaily.id, CryptoDaily.date, CryptoDaily.price_brl)
            .where(
                CryptoDaily.id.in_(ids),
                CryptoDaily.date >= self.since,
                CryptoDaily.price_brl.is_not(None),
            )
            .distinct(CryptoDaily.id)
            .order_by(CryptoDaily.id, CryptoDaily.date.desc())
        )
        return {i: Quote(price=p, date=d) for i, d, p in rows if p is not None}

    async def treasury(self, slugs: set[str]) -> Mapping[str, Quote]:
        if not slugs:
            return {}
        rows = await self.session.execute(
            select(
                TreasuryDaily.slug,
                TreasuryDaily.date,
                TreasuryDaily.sell_price,
                TreasuryDaily.buy_price,
            )
            .where(TreasuryDaily.slug.in_(slugs), TreasuryDaily.date >= self.since)
            .distinct(TreasuryDaily.slug)
            .order_by(TreasuryDaily.slug, TreasuryDaily.date.desc())
        )
        # PU de venda é o que a pessoa recebe no resgate antecipado; o de compra só
        # entra se a venda não vier no dia.
        return {
            s: Quote(price=sell if sell is not None else buy, date=d)
            for s, d, sell, buy in rows
            if sell is not None or buy is not None
        }


def _blocked(position: ValuationPosition, gate: Gate) -> str | None:
    if position.market_ref == "ticker" and not gate.prices_allowed:
        return PRICE_REASON
    if position.market_ref == "coingecko_id" and not gate.crypto_allowed:
        return CRYPTO_REASON
    return None


async def value_positions(request: ValuationRequest, prices: PriceSource, gate: Gate) -> Valuation:
    by_ref: dict[str, set[str]] = {"ticker": set(), "coingecko_id": set(), "treasury_slug": set()}
    for p in request.positions:
        if p.quantity is not None and p.market_ref in by_ref and _blocked(p, gate) is None:
            by_ref[p.market_ref].add(p.symbol)
    found: dict[str, Mapping[str, Quote]] = {
        "ticker": await prices.quotes(by_ref["ticker"]),
        "coingecko_id": await prices.crypto(by_ref["coingecko_id"]),
        "treasury_slug": await prices.treasury(by_ref["treasury_slug"]),
    }

    rows: list[ValuedPosition] = []
    for p in request.positions:
        rows.append(_value_one(p, found, gate))

    total_value = sum((r.value for r in rows if r.value is not None), Decimal(0))
    for r in rows:
        if r.value is not None and total_value > 0:
            r.weight = (r.value / total_value).quantize(RATIO)
    # Resultado total só sobre as posições que têm custo **e** valor; o resto (CDB por
    # valor, ativo sem preço) fica de fora e o `partial` avisa.
    with_result = [r for r in rows if r.result is not None and r.cost is not None]
    total_cost = sum((r.cost for r in with_result if r.cost is not None), Decimal(0))
    total_result = sum((r.result for r in with_result if r.result is not None), Decimal(0))
    dates = [r.price_date for r in rows if r.price_date is not None]
    return Valuation(
        positions=rows,
        total_value=total_value.quantize(CENT),
        total_cost=total_cost.quantize(CENT) if with_result else None,
        total_result=total_result.quantize(CENT) if with_result else None,
        partial=any(r.value is None for r in rows) or len(with_result) < len(rows),
        as_of=max(dates) if dates else None,
    )


def _value_one(
    p: ValuationPosition, found: Mapping[str, Mapping[str, Quote]], gate: Gate
) -> ValuedPosition:
    missing: dict[str, str] = {}
    cost = (
        (p.quantity * p.avg_price).quantize(CENT)
        if p.quantity is not None and p.avg_price is not None
        else None
    )
    if cost is None and p.value_brl is None:
        missing["cost"] = "preço médio desconhecido (falta o histórico de compras)"

    base = ValuedPosition(
        symbol=p.symbol,
        market_ref=p.market_ref,
        asset_class=p.asset_class,
        quantity=p.quantity,
        avg_price=p.avg_price,
        cost=cost,
        price=None,
        price_date=None,
        value=None,
        result=None,
        result_percent=None,
        weight=None,
        source=SOURCES.get(p.market_ref),
        missing_reasons=missing,
    )

    if p.value_brl is not None:
        # Posição informada por valor (CDB, LCI): o número é o da pessoa, sem fonte.
        base.value = p.value_brl.quantize(CENT)
        base.source = None
        base.missing_reasons["price"] = "posição informada por valor, sem cotação pública"
        return base

    reason = _blocked(p, gate)
    quote = found.get(p.market_ref, {}).get(p.symbol) if reason is None else None
    if quote is None:
        base.missing_reasons["price"] = reason or (
            "ativo sem cotação de mercado"
            if p.market_ref == "none"
            else f"sem preço nos últimos {STALE_AFTER_DAYS} dias"
        )
        base.missing_reasons["value"] = base.missing_reasons["price"]
        return base

    assert p.quantity is not None
    base.price = quote.price
    base.price_date = quote.date
    base.value = (p.quantity * quote.price).quantize(CENT)
    if cost is not None:
        base.result = base.value - cost
        if cost > 0:
            base.result_percent = (base.result / cost).quantize(RATIO)
    return base
