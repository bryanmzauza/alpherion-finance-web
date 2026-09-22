"""Rotas do portal de mercado (site.md §2.3, plano §3.4 e §4.2).

O que sai daqui é agregação, e agregação é onde é mais fácil um produto escorregar de
fato para opinião. As defesas estão no contrato, não no bom senso de quem escrever a
próxima rota:

- **Lista ordenada declara a métrica e o piso de liquidez** (`MoversList.metric`,
  `min_volume`), para que o título da página possa dizer "maiores altas por variação do
  dia entre papéis com mais de R$ 1 milhão negociado". Sem isso, "maiores altas" é um
  papel de R$ 3 mil que subiu com um lote.
- **Contadores são factuais**: "412 empresas listadas", nunca "as 412 melhores".
- **A agenda só traz fato com data e fonte** — quem monta é o `transform/events.py`.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.auth import require_scopes
from alpherion.db.session import get_session
from alpherion.market import cache, market_data, repository, schemas
from alpherion.market.flags import Gate
from alpherion.routers.securities import get_gate

router = APIRouter(tags=["market"], dependencies=[Depends(require_scopes("market:read"))])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
GateDep = Annotated[Gate, Depends(get_gate)]

MoverMetric = Literal["change", "volume"]
SecurityType = Literal["stock", "unit", "fii", "fiagro", "etf", "bdr"]


@router.get("/market/strip", response_model=list[schemas.StripItem])
async def get_strip(session: SessionDep, gate: GateDep) -> list[schemas.StripItem]:
    """Faixa do header. Item indisponível vem `null` com motivo — a faixa nunca mente."""
    return await cache.cached_list(
        "strip", model=schemas.StripItem, loader=lambda: _strip(session, gate)
    )


async def _strip(session: AsyncSession, gate: Gate) -> list[schemas.StripItem]:
    items = await market_data.strip(session)
    travados = []
    for item in items:
        is_crypto = item.key in {"bitcoin", "ethereum"}
        is_b3 = item.key in {"ibovespa", "ifix", "idiv", "smll"}
        if is_crypto:
            travados.append(gate.apply(item, crypto=True))
        elif is_b3:
            travados.append(gate.apply(item))
        else:
            travados.append(item)  # macro do BCB: fonte liberada
    return travados


@router.get("/market/movers", response_model=schemas.MoversList)
async def get_movers(
    session: SessionDep,
    gate: GateDep,
    metric: MoverMetric = "change",
    dir: Literal["asc", "desc"] = "desc",  # noqa: A002 - nome do parâmetro no contrato
    type: SecurityType | None = None,  # noqa: A002
    min_volume: Decimal | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> schemas.MoversList:
    """Lista do dia por uma métrica declarada, com piso de liquidez."""

    async def load() -> schemas.MoversList:
        result = await market_data.movers(
            session,
            metric=metric,
            direction=dir,
            type_=type,
            min_volume=min_volume,
            limit=limit,
        )
        return result.model_copy(update={"items": gate.apply_all(result.items)})

    return await cache.cached(
        "movers",
        metric,
        dir,
        type or "",
        min_volume or "",
        limit,
        model=schemas.MoversList,
        loader=load,
    )


@router.get("/market/events", response_model=list[schemas.MarketEvent])
async def get_events(
    session: SessionDep,
    from_: Annotated[dt.date | None, Query(alias="from")] = None,
    to: dt.date | None = None,
    kind: Literal["ex_date", "payment", "document", "macro", "corporate"] | None = None,
    ticker: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[schemas.MarketEvent]:
    """Agenda: proventos, comunicados e macro. Só fato com data e fonte."""
    return await repository.events(
        session, start=from_, end=to, kind=kind, ticker=ticker, limit=limit
    )


@router.get("/market/overview", response_model=schemas.MarketOverview)
async def get_overview(session: SessionDep, gate: GateDep) -> schemas.MarketOverview:
    """Tudo o que o portal mostra de uma vez: faixa, contadores, listas do dia e eventos."""
    return await cache.cached(
        "overview", model=schemas.MarketOverview, loader=lambda: _overview(session, gate)
    )


async def _overview(session: AsyncSession, gate: Gate) -> schemas.MarketOverview:
    gainers = await market_data.movers(session, metric="change", direction="desc")
    losers = await market_data.movers(session, metric="change", direction="asc")
    traded = await market_data.movers(session, metric="volume", direction="desc")
    hoje = dt.date.today()

    return schemas.MarketOverview(
        strip=await _strip(session, gate),
        counters=await market_data.counters(session),
        gainers=gainers.model_copy(update={"items": gate.apply_all(gainers.items)}),
        losers=losers.model_copy(update={"items": gate.apply_all(losers.items)}),
        most_traded=traded.model_copy(update={"items": gate.apply_all(traded.items)}),
        events=await repository.events(session, start=hoje, end=hoje + dt.timedelta(days=7)),
    )


@router.get("/quotes", response_model=list[schemas.QuoteItem])
async def get_quotes(
    session: SessionDep,
    gate: GateDep,
    symbols: Annotated[str, Query(min_length=1, max_length=1200)],
) -> list[schemas.QuoteItem]:
    """Cotações atuais (lista separada por vírgula) — usado pelo app na carteira."""
    return gate.apply_all(await market_data.quotes(session, symbols.split(",")))


# --- setores ----------------------------------------------------------------


@router.get("/sectors", response_model=list[schemas.SectorNode])
async def list_sectors(session: SessionDep) -> list[schemas.SectorNode]:
    """Árvore de setores, com a contagem de papéis de cada um."""
    return await cache.cached_list(
        "reference",
        "sectors",
        model=schemas.SectorNode,
        loader=lambda: market_data.sectors(session),
    )


@router.get("/sectors/{slug}", response_model=schemas.SectorNode)
async def get_sector(session: SessionDep, slug: str) -> schemas.SectorNode:
    result = await market_data.sector(session, slug)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"setor não encontrado: {slug}")
    return result


# --- índices ----------------------------------------------------------------


@router.get("/indices", response_model=list[schemas.IndexSummary])
async def list_indices(session: SessionDep) -> list[schemas.IndexSummary]:
    return await cache.cached_list(
        "reference",
        "indices",
        model=schemas.IndexSummary,
        loader=lambda: market_data.indices(session),
    )


@router.get("/indices/{slug}", response_model=schemas.IndexDetail)
async def get_index(session: SessionDep, gate: GateDep, slug: str) -> schemas.IndexDetail:
    result = await market_data.index_detail(session, slug)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"índice não encontrado: {slug}")
    return gate.apply(result)


@router.get("/indices/{slug}/composition", response_model=schemas.IndexCompositionResult)
async def get_index_composition(
    session: SessionDep,
    slug: str,
    date: dt.date | None = None,
) -> schemas.IndexCompositionResult:
    """Carteira teórica. A data de referência vem na resposta — é parte do dado."""
    result = await market_data.index_composition(session, slug, reference=date)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"sem carteira carregada para {slug}")
    return result


@router.get("/indices/{slug}/history", response_model=list[schemas.IndexPoint])
async def get_index_history(
    session: SessionDep,
    gate: GateDep,
    slug: str,
    days: Annotated[int, Query(ge=1, le=3650)] = 365,
) -> list[schemas.IndexPoint]:
    return gate.apply_all(await market_data.index_history(session, slug, days=days))


# --- Tesouro ----------------------------------------------------------------


@router.get("/treasury", response_model=list[schemas.TreasuryBondItem])
async def list_treasury(session: SessionDep) -> list[schemas.TreasuryBondItem]:
    """Títulos do Tesouro. Fonte ODbL: **não** passa pela trava da B3 (ADR-017)."""
    return await cache.cached_list(
        "quote",
        "treasury",
        model=schemas.TreasuryBondItem,
        loader=lambda: market_data.treasury(session),
    )


@router.get("/treasury/{slug}/history", response_model=list[schemas.TreasuryPoint])
async def get_treasury_history(
    session: SessionDep,
    slug: str,
    days: Annotated[int, Query(ge=1, le=3650)] = 365,
) -> list[schemas.TreasuryPoint]:
    return await market_data.treasury_history(session, slug, days=days)


# --- cripto -----------------------------------------------------------------


@router.get("/crypto", response_model=list[schemas.CryptoItem])
async def list_crypto(
    session: SessionDep,
    gate: GateDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[schemas.CryptoItem]:
    return gate.apply_all(await market_data.crypto_list(session, limit=limit), crypto=True)


@router.get("/crypto/{asset_id}/history", response_model=list[schemas.CryptoPoint])
async def get_crypto_history(
    session: SessionDep,
    gate: GateDep,
    asset_id: str,
    days: Annotated[int, Query(ge=1, le=3650)] = 365,
) -> list[schemas.CryptoPoint]:
    points = await market_data.crypto_history(session, asset_id, days=days)
    return gate.apply_all(points, crypto=True)


# --- Leitura de Mercado -----------------------------------------------------


@router.post("/market/weekly-reading", response_model=schemas.WeeklyReading)
async def weekly_reading(
    session: SessionDep,
    gate: GateDep,
    reference_date: dt.date | None = None,
) -> schemas.WeeklyReading:
    """Números da Leitura de Mercado — endpoint **interno** (§2.3).

    Mesmo cálculo de `ferramentas/leitura-semanal.py`, mas sobre as nossas tabelas: é o
    que garante que o número do vídeo e o número do site sejam o mesmo número.

    `POST` e não `GET` porque o cálculo percorre um ano de série de cinco ativos e não é
    idempotente do ponto de vista de custo — não é resposta para cachear em borda.

    A trava do ADR-017 vale aqui como em qualquer outra saída: sem licença, os preços
    vêm `null` com o motivo. O vídeo é publicação como qualquer outra.
    """
    result = await market_data.weekly_reading(session, reference=reference_date)
    return result.model_copy(update={"snapshot": gate.apply_all(result.snapshot)})
