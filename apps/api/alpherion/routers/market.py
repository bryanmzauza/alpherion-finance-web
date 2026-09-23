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
    """Faixa do header: os cinco itens de `HEADER_STRIP_KEYS`, resposta mínima (§2.1).

    Item indisponível vem `null` com motivo — a faixa nunca mente. A faixa completa,
    com os nove itens, sai em `/market/overview`.
    """
    return await cache.cached_list(
        "strip",
        model=schemas.StripItem,
        loader=lambda: _strip(session, gate, keys=market_data.HEADER_STRIP_KEYS),
    )


async def _strip(
    session: AsyncSession, gate: Gate, *, keys: tuple[str, ...] | None = None
) -> list[schemas.StripItem]:
    items = await market_data.strip(session, keys)
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


EventKind = Literal["ex_date", "payment", "document", "macro", "corporate"]

#: Janela máxima de uma consulta à agenda. Um mês e pouco cobre a vista mensal; mais
#: que isso é varredura, e varredura não é o que uma página pede.
MAX_EVENTS_WINDOW = dt.timedelta(days=42)


def _window(start: dt.date | None, end: dt.date | None) -> tuple[dt.date, dt.date]:
    first = start or dt.date.today()
    last = end or first + dt.timedelta(days=7)
    if last < first:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="`to` antes de `from`")
    if last - first > MAX_EVENTS_WINDOW:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"janela da agenda passa de {MAX_EVENTS_WINDOW.days} dias",
        )
    return first, last


@router.get("/market/events", response_model=list[schemas.MarketEvent])
async def get_events(
    session: SessionDep,
    from_: Annotated[dt.date | None, Query(alias="from")] = None,
    to: dt.date | None = None,
    kind: Annotated[list[EventKind] | None, Query()] = None,
    type: SecurityType | None = None,  # noqa: A002 - nome do parâmetro no contrato
    ticker: str | None = None,
    category: Annotated[list[str] | None, Query(max_length=10)] = None,
    limit: Annotated[int, Query(ge=1, le=repository.MAX_EVENTS)] = 100,
) -> list[schemas.MarketEvent]:
    """Agenda: proventos, comunicados e macro. Só fato com data e fonte.

    `kind` e `category` aceitam vários valores (`?kind=ex_date&kind=payment`).
    `category` filtra só comunicados — "Fato Relevante" é a categoria da própria CVM,
    não um juízo nosso sobre o que é relevante.
    """
    first, last = _window(from_, to)
    return await repository.events(
        session,
        start=first,
        end=last,
        kind=kind,
        type_=type,
        ticker=ticker,
        document_categories=category,
        limit=limit,
    )


@router.get("/market/events/calendar", response_model=list[schemas.EventCount])
async def get_event_counts(
    session: SessionDep,
    from_: Annotated[dt.date | None, Query(alias="from")] = None,
    to: dt.date | None = None,
    kind: Annotated[list[EventKind] | None, Query()] = None,
    type: SecurityType | None = None,  # noqa: A002
    category: Annotated[list[str] | None, Query(max_length=10)] = None,
) -> list[schemas.EventCount]:
    """Quantos eventos de cada tipo caem em cada dia — a vista mensal da `/agenda`."""
    first, last = _window(from_, to)
    return await repository.event_counts(
        session, start=first, end=last, kind=kind, type_=type, document_categories=category
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


@router.get("/sectors/{slug}", response_model=schemas.SectorDetail)
async def get_sector(session: SessionDep, gate: GateDep, slug: str) -> schemas.SectorDetail:
    """O setor e os agregados factuais. Os papéis vêm de `/securities?sector=`."""
    result = await market_data.sector(session, slug)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"setor não encontrado: {slug}")
    return gate.apply(result)


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
