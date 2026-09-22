"""Leitura do schema `market` (a API só lê; quem escreve é o worker `data`).

Aqui mora todo SQL das rotas de mercado, por dois motivos:

- **A ordenação é de lista fechada.** `SORTABLE` é a única porta: o cliente manda o nome
  de um campo permitido, nunca SQL. Além da injeção, é o que garante que uma ordenação
  nova seja uma decisão de produto — "maior dividend yield 12 m" é fato ordenado por um
  número, e a página tem de poder dizer qual (§4.5 do plano, ADR-018).
- **Nenhuma consulta sem limite.** Toda lista é paginada com teto de 100 (§2.3), e o
  histórico é cortado por intervalo: o usuário `api` tem `statement_timeout` de 5 s, e
  uma consulta sem limite vira erro em produção no pior momento.

As funções devolvem os modelos de `schemas.py` já montados, com a fonte de cada bloco —
a trava de licença (`flags.Gate`) é aplicada depois, na rota.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.db.models import (
    CompanyDocument,
    CorporateAction,
    DailyQuote,
    DataSource,
    FinancialStatement,
    IndicatorDaily,
    Security,
)
from alpherion.db.models import MarketEvent as MarketEventRow
from alpherion.market import schemas

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE: Final = 100
DEFAULT_PAGE_SIZE: Final = 50

#: Ordenações permitidas: nome público → coluna. Fora desta lista, a rota devolve 422.
#: Nada aqui é "melhor" nem "pior" — é o critério que o usuário escolheu.
SORTABLE: Final[dict[str, Any]] = {
    "ticker": Security.ticker,
    "company_name": Security.company_name,
    "volume": DailyQuote.volume,
    "change": DailyQuote.close,
    "dy_12m": IndicatorDaily.dy_12m,
    "pe": IndicatorDaily.pe,
    "pb": IndicatorDaily.pb,
    "pvp": IndicatorDaily.pvp,
    "roe": IndicatorDaily.roe,
    "market_cap": IndicatorDaily.market_cap,
}

#: Ordem padrão: **liquidez**, que é neutra. Alfabética privilegiaria o começo do
#: alfabeto; qualquer indicador de valuation insinuaria uma recomendação (ADR-018).
DEFAULT_SORT: Final = "volume"

#: Intervalos aceitos no histórico, em dias. `max` é o que houver.
RANGES: Final[dict[str, int | None]] = {
    "1m": 31,
    "6m": 186,
    "1a": 366,
    "5a": 1827,
    "max": None,
}


async def source_ref(
    session: AsyncSession, source: str, *, document: str | None = None
) -> schemas.SourceRef:
    """A origem de um bloco, lida de `data_sources` — a mesma tabela que trava a carga."""
    row = (
        await session.execute(
            select(DataSource.attribution, DataSource.last_loaded_at).where(
                DataSource.source == source
            )
        )
    ).first()
    if row is None:
        return schemas.SourceRef(source=source, attribution=f"Fonte: {source.upper()}")
    return schemas.SourceRef(
        source=source,
        attribution=row[0],
        document=document,
        updated_at=row[1],
    )


# --- busca e listas ---------------------------------------------------------


async def search(
    session: AsyncSession, query: str, *, limit: int = 20
) -> list[schemas.SecuritySummary]:
    """Busca por ticker ou nome, sem acento e sem caixa.

    O ticker exato vem primeiro: quem digita "PETR4" quer a PETR4, não a primeira
    empresa cujo nome contenha "petr".
    """
    term = query.strip()
    if len(term) < 2:
        return []
    like = f"%{term.lower()}%"
    statement = (
        select(Security)
        .where(
            Security.status == "active",
            or_(
                func.lower(Security.ticker).like(like),
                text(
                    "market.immutable_unaccent(lower(securities.company_name)) LIKE "
                    "market.immutable_unaccent(:termo)"
                ).bindparams(termo=like),
            ),
        )
        .order_by(
            (func.lower(Security.ticker) == term.lower()).desc(),
            func.lower(Security.ticker).startswith(term.lower()).desc(),
            Security.ticker,
        )
        .limit(min(limit, MAX_PAGE_SIZE))
    )
    rows = (await session.execute(statement)).scalars().all()
    return [_summary(row) for row in rows]


async def list_securities(
    session: AsyncSession,
    *,
    type_: str | None = None,
    sector_slug: str | None = None,
    sort: str = DEFAULT_SORT,
    descending: bool = True,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    min_volume: Decimal | None = None,
) -> schemas.Page[schemas.SecuritySummary]:
    """Lista paginada de papéis, ordenada pelo critério **que o cliente escolheu**."""
    if sort not in SORTABLE:
        raise ValueError(f"ordenação não permitida: {sort!r}")
    size = max(1, min(page_size, MAX_PAGE_SIZE))
    latest = await _latest_quote_date(session)

    base = select(Security).where(Security.status == "active")
    if type_:
        base = base.where(Security.type == type_)
    if sector_slug:
        base = base.where(Security.sector_slug == sector_slug)

    joined = _with_market_data(base, latest)
    if min_volume is not None:
        joined = joined.where(DailyQuote.volume >= min_volume)

    total = (
        await session.execute(select(func.count()).select_from(joined.subquery()))
    ).scalar() or 0

    column = SORTABLE[sort]
    ordering = column.desc().nulls_last() if descending else column.asc().nulls_last()
    rows = (
        await session.execute(
            joined.add_columns(DailyQuote.close, DailyQuote.volume)
            .order_by(ordering, Security.ticker)
            .offset((max(1, page) - 1) * size)
            .limit(size)
        )
    ).all()

    return schemas.Page(
        items=[_summary(row[0], close=row[1], volume=row[2]) for row in rows],
        total=total,
        page=max(1, page),
        page_size=size,
    )


def _with_market_data(statement: Select[Any], quote_date: date | None) -> Select[Any]:
    """Junta cotação do último pregão e indicadores do dia, sem perder papel sem preço.

    `outerjoin` de propósito: papel sem cotação (fonte não licenciada, papel novo) tem
    de continuar aparecendo na lista, com "—" no lugar do preço.
    """
    return statement.outerjoin(
        DailyQuote,
        (DailyQuote.ticker == Security.ticker) & (DailyQuote.date == quote_date),
    ).outerjoin(
        IndicatorDaily,
        (IndicatorDaily.ticker == Security.ticker) & (IndicatorDaily.date == quote_date),
    )


async def _latest_quote_date(session: AsyncSession) -> date | None:
    return (await session.execute(select(func.max(DailyQuote.date)))).scalar()


def _summary(
    row: Security,
    *,
    close: Decimal | None = None,
    volume: Decimal | None = None,
) -> schemas.SecuritySummary:
    return schemas.SecuritySummary(
        ticker=row.ticker,
        type=row.type,
        company_name=row.company_name,
        trade_name=row.trade_name,
        sector_slug=row.sector_slug,
        price=close,
        volume=volume,
    )


# --- página do ativo --------------------------------------------------------


async def get_security(session: AsyncSession, ticker: str) -> schemas.SecurityDetail | None:
    """Perfil, cabeçalho de preço e indicadores — cada bloco com a **sua** fonte."""
    code = ticker.strip().upper()
    security = (
        await session.execute(select(Security).where(Security.ticker == code))
    ).scalar_one_or_none()
    if security is None:
        return None

    profile = schemas.SecurityProfile(
        source=await source_ref(session, "b3", document="Listagem B3"),
        ticker=security.ticker,
        type=security.type,
        company_name=security.company_name,
        trade_name=security.trade_name,
        cnpj=security.cnpj,
        cvm_code=security.cvm_code,
        isin=security.isin,
        sector=security.sector,
        subsector=security.subsector,
        segment=security.segment,
        sector_slug=security.sector_slug,
        listing_segment=security.listing_segment,
        etf_index_slug=security.etf_index_slug,
        bdr_ratio=security.bdr_ratio,
        status=security.status,
    )
    return schemas.SecurityDetail(
        profile=profile,
        price=await _price_header(session, code),
        indicators=await _indicators(session, code),
    )


async def _price_header(session: AsyncSession, ticker: str) -> schemas.PriceHeader:
    last = (
        (
            await session.execute(
                select(DailyQuote)
                .where(DailyQuote.ticker == ticker)
                .order_by(DailyQuote.date.desc())
                .limit(2)
            )
        )
        .scalars()
        .all()
    )

    source = await source_ref(session, "b3", document="COTAHIST")
    if not last:
        return schemas.PriceHeader(
            source=source,
            ticker=ticker,
            missing_reasons={"price": "sem cotação carregada para este papel"},
        )

    today, previous = last[0], last[1] if len(last) > 1 else None
    change = None
    change_pct = None
    if previous is not None and previous.close:
        change = Decimal(str(today.close)) - Decimal(str(previous.close))
        change_pct = change / Decimal(str(previous.close))

    window = today.date - timedelta(days=365)
    extremes = (
        await session.execute(
            select(func.min(DailyQuote.low), func.max(DailyQuote.high)).where(
                DailyQuote.ticker == ticker, DailyQuote.date >= window
            )
        )
    ).first()

    return schemas.PriceHeader(
        source=schemas.SourceRef(
            source=source.source,
            attribution=source.attribution,
            document=f"pregão de {today.date:%d/%m/%Y}",
            updated_at=source.updated_at,
        ),
        ticker=ticker,
        price=today.close,
        change_day=change,
        change_percent_day=change_pct,
        low_52w=extremes[0] if extremes else None,
        high_52w=extremes[1] if extremes else None,
        volume=today.volume,
        quote_date=today.date,
    )


async def _indicators(session: AsyncSession, ticker: str) -> schemas.Indicators:
    row = (
        await session.execute(
            select(IndicatorDaily)
            .where(IndicatorDaily.ticker == ticker)
            .order_by(IndicatorDaily.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    document = None
    if row is not None and row.inputs:
        period = row.inputs.get("period_end")
        document = f"DFP {period[:4]}" if isinstance(period, str) else None
    source = await source_ref(session, "cvm", document=document)

    if row is None:
        return schemas.Indicators(
            source=source,
            missing_reasons={"indicadores": "ainda não calculados para este papel"},
        )

    campos = {
        name: getattr(row, name, None)
        for name in schemas.Indicators.model_fields
        if name not in {"source", "missing_reasons", "date"}
    }
    return schemas.Indicators(
        source=source,
        date=row.date,
        missing_reasons={k: str(v) for k, v in (row.missing_reasons or {}).items()},
        **campos,
    )


async def history(
    session: AsyncSession,
    ticker: str,
    *,
    range_: str = "1a",
    adjusted: bool = True,
) -> list[schemas.Quote]:
    """OHLCV diário. `adjusted` usa a coluna ajustada por proventos e eventos."""
    if range_ not in RANGES:
        raise ValueError(f"intervalo inválido: {range_!r}")
    statement = select(DailyQuote).where(DailyQuote.ticker == ticker.upper())
    days = RANGES[range_]
    if days is not None:
        statement = statement.where(DailyQuote.date >= date.today() - timedelta(days=days))

    rows = (await session.execute(statement.order_by(DailyQuote.date))).scalars().all()
    return [
        schemas.Quote(
            date=row.date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close_adjusted if adjusted and row.close_adjusted else row.close,
            close_adjusted=row.close_adjusted,
            volume=row.volume,
        )
        for row in rows
    ]


async def dividends(
    session: AsyncSession, ticker: str, *, limit: int = MAX_PAGE_SIZE
) -> list[schemas.CorporateEvent]:
    rows = (
        (
            await session.execute(
                select(CorporateAction)
                .where(CorporateAction.ticker == ticker.upper())
                .order_by(CorporateAction.ex_date.desc().nulls_last())
                .limit(min(limit, MAX_PAGE_SIZE))
            )
        )
        .scalars()
        .all()
    )
    return [_event(row) for row in rows]


async def upcoming_events(
    session: AsyncSession, ticker: str, *, since: date | None = None
) -> list[schemas.CorporateEvent]:
    """Data-com e pagamentos **anunciados** daqui para a frente — fato, não previsão."""
    start = since or date.today()
    rows = (
        (
            await session.execute(
                select(CorporateAction)
                .where(
                    CorporateAction.ticker == ticker.upper(),
                    or_(
                        CorporateAction.ex_date >= start,
                        CorporateAction.payment_date >= start,
                    ),
                )
                .order_by(CorporateAction.ex_date.asc().nulls_last())
                .limit(MAX_PAGE_SIZE)
            )
        )
        .scalars()
        .all()
    )
    return [_event(row) for row in rows]


def _event(row: CorporateAction) -> schemas.CorporateEvent:
    return schemas.CorporateEvent(
        kind=row.kind,
        ex_date=row.ex_date,
        record_date=row.record_date,
        payment_date=row.payment_date,
        value_per_share=row.value_per_share,
        ratio=row.ratio,
        source=row.source,
    )


async def documents(
    session: AsyncSession,
    ticker: str,
    *,
    category: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> schemas.Page[schemas.Document]:
    """Comunicados entregues à CVM. Metadados e link — o texto fica na CVM (§8.3)."""
    size = max(1, min(page_size, MAX_PAGE_SIZE))
    statement = select(CompanyDocument).where(CompanyDocument.ticker == ticker.upper())
    if category:
        statement = statement.where(CompanyDocument.category == category)

    total = (
        await session.execute(select(func.count()).select_from(statement.subquery()))
    ).scalar() or 0
    rows = (
        (
            await session.execute(
                statement.order_by(CompanyDocument.delivered_at.desc())
                .offset((max(1, page) - 1) * size)
                .limit(size)
            )
        )
        .scalars()
        .all()
    )

    return schemas.Page(
        items=[
            schemas.Document(
                protocol=row.protocol,
                category=row.category,
                type=row.type,
                subject=row.subject,
                delivered_at=row.delivered_at,
                reference_date=row.reference_date,
                url=row.url,
            )
            for row in rows
        ],
        total=total,
        page=max(1, page),
        page_size=size,
    )


async def financials(
    session: AsyncSession, ticker: str, *, period_type: str = "annual"
) -> schemas.Financials | None:
    """Demonstrações do período mais recente publicado, no formato longo da CVM."""
    security = (
        await session.execute(select(Security.cvm_code).where(Security.ticker == ticker.upper()))
    ).scalar_one_or_none()
    if security is None:
        return None

    period = (
        await session.execute(
            select(func.max(FinancialStatement.period_end)).where(
                FinancialStatement.cvm_code == security,
                FinancialStatement.period_type == period_type,
            )
        )
    ).scalar()
    if period is None:
        return None

    rows = (
        (
            await session.execute(
                select(FinancialStatement).where(
                    FinancialStatement.cvm_code == security,
                    FinancialStatement.period_end == period,
                    FinancialStatement.period_type == period_type,
                )
            )
        )
        .scalars()
        .all()
    )

    consolidated = any(row.consolidated for row in rows)
    grouped: dict[str, list[schemas.StatementLine]] = {}
    for row in rows:
        if row.consolidated != consolidated:
            continue  # nunca misturar consolidado com individual na mesma tabela
        grouped.setdefault(row.statement, []).append(
            schemas.StatementLine(
                account_code=row.account_code,
                account_name=row.account_name,
                value=row.value,
            )
        )
    for lines in grouped.values():
        lines.sort(key=lambda line: line.account_code)

    return schemas.Financials(
        source=await source_ref(session, "cvm", document=f"DFP {period:%Y}"),
        period_end=period,
        period_type=period_type,
        consolidated=consolidated,
        statements=grouped,
    )


# --- agenda -----------------------------------------------------------------


async def events(
    session: AsyncSession,
    *,
    start: date | None = None,
    end: date | None = None,
    kind: str | None = None,
    ticker: str | None = None,
    limit: int = MAX_PAGE_SIZE,
) -> list[schemas.MarketEvent]:
    first = start or date.today()
    last = end or first + timedelta(days=7)
    statement = select(MarketEventRow).where(MarketEventRow.date.between(first, last))
    if kind:
        statement = statement.where(MarketEventRow.kind == kind)
    if ticker:
        statement = statement.where(MarketEventRow.ticker == ticker.upper())

    rows = (
        (
            await session.execute(
                statement.order_by(MarketEventRow.date, MarketEventRow.id).limit(
                    min(limit, MAX_PAGE_SIZE)
                )
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas.MarketEvent(
            id=row.id,
            kind=row.kind,
            date=row.date,
            ticker=row.ticker,
            title=row.title,
            payload=row.payload,
            source=row.source,
        )
        for row in rows
    ]
