"""Leitura das visões do portal: faixa, listas do dia, setores, índices, Tesouro e cripto.

Separado de `repository.py` (que cuida da página do ativo) porque as perguntas são de
outra natureza: aqui quase tudo é agregação sobre o último pregão, e o cuidado principal
é **não deixar uma agregação virar opinião**.

Duas regras concretas:

- **Lista ordenada declara a métrica.** "Maiores altas" é fato quando o contrato diz que
  a ordem é por variação do dia entre papéis acima de um volume mínimo. Sem a métrica e
  sem o piso de liquidez, a mesma lista vira um ranking editorial (ADR-018).
- **Piso de liquidez obrigatório nas listas do dia.** Sem ele, "maior alta" é sempre um
  papel de R$ 3 mil negociados, que sobe 40% por causa de um lote. Isso não informa
  nada e induz a erro — o padrão é `MIN_VOLUME_DEFAULT`.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import Row, Select, func, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from alpherion.db.models import (
    CryptoAsset,
    CryptoDaily,
    CryptoMetric,
    DailyQuote,
    IndexComposition,
    IndexDaily,
    IndicatorDaily,
    MacroSeries,
    MarketIndex,
    Sector,
    Security,
    TreasuryBond,
    TreasuryDaily,
)
from alpherion.market import accumulated, repository, schemas, weekly

logger = logging.getLogger(__name__)

#: Piso de liquidez das listas do dia, em R$ de volume financeiro. Um papel abaixo disso
#: sobe 40% com um lote — a lista informaria ruído, não mercado.
MIN_VOLUME_DEFAULT: Final = Decimal("1000000")

#: Métricas aceitas em `/market/movers`. Fora daqui, 422.
MOVER_METRICS: Final = ("change", "volume")

#: A faixa completa de `/mercado`, na ordem em que aparece (§2.1, §4.2 do plano).
#: `macro_12m` é acumulado composto (`accumulated.py`); `macro` é o último ponto da série.
STRIP_ITEMS: Final[tuple[tuple[str, str, str], ...]] = (
    ("ibovespa", "Ibovespa", "index"),
    ("ifix", "IFIX", "index"),
    ("idiv", "IDIV", "index"),
    ("smll", "SMLL", "index"),
    ("ptax_venda", "Dólar (PTAX)", "macro"),
    ("selic_meta", "Selic (meta)", "macro"),
    ("cdi_12m", "CDI 12 m", "macro_12m"),
    ("ipca_12m", "IPCA 12 m", "macro_12m"),
    ("bitcoin", "Bitcoin", "crypto"),
)

#: A faixa do header de toda página pública: cinco itens, resposta mínima (§2.1).
HEADER_STRIP_KEYS: Final = ("ibovespa", "ifix", "ptax_venda", "cdi_12m", "bitcoin")

#: Série do SGS de onde sai cada acumulado, e se ela é diária ou mensal.
ACCUMULATED_SERIES: Final[dict[str, tuple[str, str]]] = {
    "cdi_12m": ("cdi", "daily"),
    "ipca_12m": ("ipca", "monthly"),
}

UNITS: Final[dict[str, str]] = {"index": "pts", "macro": "%", "crypto": "BRL"}


# --- faixa do header --------------------------------------------------------


async def strip(
    session: AsyncSession, keys: Sequence[str] | None = None
) -> list[schemas.StripItem]:
    """A faixa: índices, câmbio, juros, inflação e BTC — toda ou só os `keys` pedidos.

    Item indisponível vem com valor `null` e motivo — a faixa nunca some nem mostra
    zero, porque uma faixa com buraco é mais honesta que uma faixa inventada.
    """
    wanted = set(keys) if keys is not None else None
    items: list[schemas.StripItem] = []
    for key, label, kind in STRIP_ITEMS:
        if wanted is not None and key not in wanted:
            continue
        if kind == "index":
            items.append(await _strip_index(session, key, label))
        elif kind == "macro":
            items.append(await _strip_macro(session, key, label))
        elif kind == "macro_12m":
            items.append(await _strip_accumulated(session, key, label))
        else:
            items.append(await _strip_crypto(session, key, label))
    return items


async def _strip_index(session: AsyncSession, slug: str, label: str) -> schemas.StripItem:
    row = (
        await session.execute(
            select(IndexDaily.value, IndexDaily.change_pct, IndexDaily.date)
            .where(IndexDaily.slug == slug)
            .order_by(IndexDaily.date.desc())
            .limit(1)
        )
    ).first()
    source = await repository.source_ref(session, "b3", document="Índices B3")
    if row is None:
        return schemas.StripItem(
            source=source,
            key=slug,
            label=label,
            unit=UNITS["index"],
            missing_reasons={"value": "índice ainda não carregado"},
        )
    return schemas.StripItem(
        source=source.model_copy(update={"document": f"fechamento de {row[2]:%d/%m/%Y}"}),
        key=slug,
        label=label,
        value=row[0],
        change_percent=row[1],
        unit=UNITS["index"],
    )


async def _strip_macro(session: AsyncSession, series: str, label: str) -> schemas.StripItem:
    row = (
        await session.execute(
            select(MacroSeries.value, MacroSeries.date)
            .where(MacroSeries.series == series)
            .order_by(MacroSeries.date.desc())
            .limit(1)
        )
    ).first()
    source = await repository.source_ref(session, "bcb", document="SGS/BCB")
    if row is None:
        return schemas.StripItem(
            source=source,
            key=series,
            label=label,
            missing_reasons={"value": "série ainda não carregada"},
        )
    unit = "R$" if series.startswith("ptax") else UNITS["macro"]
    return schemas.StripItem(
        source=source.model_copy(update={"document": f"SGS · {row[1]:%d/%m/%Y}"}),
        key=series,
        label=label,
        value=row[0],
        unit=unit,
    )


async def _strip_accumulated(session: AsyncSession, key: str, label: str) -> schemas.StripItem:
    """CDI e IPCA acumulados em 12 meses, compostos a partir da série do SGS."""
    series, cadence = ACCUMULATED_SERIES[key]
    # 400 dias cobrem os 12 meses com folga para feriados; 14 meses, os 12 do IPCA.
    since = dt.date.today() - dt.timedelta(days=400 if cadence == "daily" else 430)
    rows = (
        await session.execute(
            select(MacroSeries.date, MacroSeries.value)
            .where(MacroSeries.series == series, MacroSeries.date >= since)
            .order_by(MacroSeries.date)
        )
    ).all()
    points = [(row[0], row[1]) for row in rows if row[1] is not None]
    compose = accumulated.daily_12m if cadence == "daily" else accumulated.monthly_12m
    result = compose(points)

    source = await repository.source_ref(session, "bcb", document="SGS/BCB")
    if result.as_of is not None:
        source = source.model_copy(
            update={"document": f"SGS · acumulado em 12 meses até {result.as_of:%d/%m/%Y}"}
        )
    return schemas.StripItem(
        source=source,
        key=key,
        label=label,
        value=result.value,
        unit=UNITS["macro"],
        missing_reasons={"value": result.reason} if result.reason else {},
    )


async def _strip_crypto(session: AsyncSession, asset_id: str, label: str) -> schemas.StripItem:
    row = (
        await session.execute(
            select(CryptoMetric.price_brl, CryptoMetric.change_24h, CryptoMetric.captured_at)
            .where(CryptoMetric.id == asset_id)
            .order_by(CryptoMetric.captured_at.desc())
            .limit(1)
        )
    ).first()
    source = await repository.source_ref(session, "coingecko")
    if row is None:
        return schemas.StripItem(
            source=source,
            key=asset_id,
            label=label,
            unit=UNITS["crypto"],
            missing_reasons={"value": "cripto ainda não carregada"},
        )
    return schemas.StripItem(
        source=source,
        key=asset_id,
        label=label,
        value=row[0],
        change_percent=row[1],
        unit=UNITS["crypto"],
    )


# --- listas do dia ----------------------------------------------------------


async def movers(
    session: AsyncSession,
    *,
    metric: str = "change",
    direction: str = "desc",
    type_: str | None = None,
    min_volume: Decimal | None = None,
    limit: int = 10,
) -> schemas.MoversList:
    """Papéis do dia ordenados por **uma** métrica declarada, com piso de liquidez."""
    if metric not in MOVER_METRICS:
        raise ValueError(f"métrica não permitida: {metric!r}")
    floor = MIN_VOLUME_DEFAULT if min_volume is None else min_volume
    today = await _latest_quote_date(session)
    source = await repository.source_ref(session, "b3", document="COTAHIST")

    if today is None:
        return schemas.MoversList(
            source=source,
            metric=metric,
            direction=direction,
            min_volume=floor,
            items=[],
            missing_reasons={"items": "nenhum pregão carregado"},
        )

    previous = await _previous_quote_date(session, today)
    statement = _movers_query(today, previous, type_=type_, floor=floor)
    column = (
        statement.exported_columns["change_percent"]
        if metric == "change"
        else statement.exported_columns["volume"]
    )
    ordered = column.desc().nulls_last() if direction == "desc" else column.asc().nulls_last()

    rows = (await session.execute(statement.order_by(ordered).limit(min(limit, 50)))).all()
    return schemas.MoversList(
        source=source.model_copy(update={"document": f"pregão de {today:%d/%m/%Y}"}),
        metric=metric,
        direction=direction,
        min_volume=floor,
        items=[
            schemas.Mover(
                ticker=row.ticker,
                type=row.type,
                company_name=row.company_name,
                price=row.close,
                change_percent=row.change_percent,
                volume=row.volume,
            )
            for row in rows
        ],
    )


def _movers_query(
    today: dt.date,
    previous: dt.date | None,
    *,
    type_: str | None,
    floor: Decimal,
) -> Select[Any]:
    """Variação do dia = fechamento de hoje sobre o do pregão anterior."""
    anterior = (
        select(DailyQuote.ticker, DailyQuote.close.label("previous_close"))
        .where(DailyQuote.date == previous)
        .subquery()
    )

    # Sem pregão anterior (primeiro dia carregado), a variação é desconhecida — e
    # `null` é a resposta certa: zero diria "não variou", o que não foi medido.
    change = (
        ((DailyQuote.close - anterior.c.previous_close) / anterior.c.previous_close)
        if previous is not None
        else null()
    )
    statement = (
        select(
            Security.ticker,
            Security.type,
            Security.company_name,
            DailyQuote.close.label("close"),
            change.label("change_percent"),
            DailyQuote.volume.label("volume"),
        )
        .join(DailyQuote, DailyQuote.ticker == Security.ticker)
        .outerjoin(anterior, anterior.c.ticker == Security.ticker)
        .where(
            DailyQuote.date == today,
            DailyQuote.volume >= floor,
            Security.status == "active",
        )
    )
    if type_:
        statement = statement.where(Security.type == type_)
    return statement


async def _latest_quote_date(session: AsyncSession) -> dt.date | None:
    return (await session.execute(select(func.max(DailyQuote.date)))).scalar()


async def _previous_quote_date(session: AsyncSession, today: dt.date) -> dt.date | None:
    return (
        await session.execute(select(func.max(DailyQuote.date)).where(DailyQuote.date < today))
    ).scalar()


# --- contadores do portal ---------------------------------------------------


async def counters(session: AsyncSession) -> dict[str, int]:
    """Contagens factuais por classe — "1.234 empresas listadas", sem adjetivo."""
    rows = (
        await session.execute(
            select(Security.type, func.count())
            .where(Security.status == "active")
            .group_by(Security.type)
        )
    ).all()
    contagens = {str(kind): int(total) for kind, total in rows}
    rows_por_tipo = (
        await session.execute(select(Sector.kind, func.count()).group_by(Sector.kind))
    ).all()
    por_tipo: dict[str, int] = {str(kind): int(total) for kind, total in rows_por_tipo}
    contagens["sectors"] = int(sum(por_tipo.values()))
    # "Nº de setores" das ações e "nº de segmentos" dos FIIs são contagens diferentes
    # na página (§2.1): uma árvore não mistura com a outra.
    contagens["b3_segments"] = int(por_tipo.get("b3_segment", 0))
    contagens["fii_segments"] = int(por_tipo.get("fii_segment", 0))
    contagens["indices"] = int(
        (await session.execute(select(func.count()).select_from(MarketIndex))).scalar() or 0
    )
    contagens["treasury"] = int(
        (await session.execute(select(func.count()).select_from(TreasuryBond))).scalar() or 0
    )
    contagens["crypto"] = int(
        (await session.execute(select(func.count()).select_from(CryptoAsset))).scalar() or 0
    )
    return contagens


# --- setores ----------------------------------------------------------------


async def sectors(session: AsyncSession) -> list[schemas.SectorNode]:
    rows = (
        (
            await session.execute(
                select(Sector).order_by(Sector.sector, Sector.subsector, Sector.name)
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas.SectorNode(
            slug=row.slug,
            name=row.name,
            kind=row.kind,
            sector=row.sector,
            subsector=row.subsector,
            securities_count=row.securities_count,
        )
        for row in rows
    ]


async def sector(session: AsyncSession, slug: str) -> schemas.SectorDetail | None:
    """O setor e os agregados factuais: contagem e valor de mercado somado."""
    row = (await session.execute(select(Sector).where(Sector.slug == slug))).scalar_one_or_none()
    if row is None:
        return None

    latest = await _latest_quote_date(session)
    total, counted = None, 0
    if latest is not None:
        total, counted = (
            await session.execute(
                select(func.sum(IndicatorDaily.market_cap), func.count(IndicatorDaily.market_cap))
                .join(Security, Security.ticker == IndicatorDaily.ticker)
                .where(
                    Security.sector_slug == slug,
                    Security.status == "active",
                    IndicatorDaily.date == latest,
                )
            )
        ).one()

    source = await repository.source_ref(session, "b3", document="classificação setorial B3")
    reasons: dict[str, str] = {}
    if total is None:
        reasons["market_cap"] = "sem valor de mercado calculado para os papéis do setor"
    elif latest is not None:
        source = source.model_copy(update={"document": f"pregão de {latest:%d/%m/%Y}"})
    return schemas.SectorDetail(
        source=source,
        missing_reasons=reasons,
        slug=row.slug,
        name=row.name,
        kind=row.kind,
        sector=row.sector,
        subsector=row.subsector,
        securities_count=row.securities_count,
        market_cap=total,
        market_cap_count=int(counted or 0),
    )


# --- índices ----------------------------------------------------------------


async def indices(session: AsyncSession) -> list[schemas.IndexSummary]:
    rows = (await session.execute(select(MarketIndex).order_by(MarketIndex.name))).scalars().all()
    return [schemas.IndexSummary(slug=row.slug, b3_code=row.b3_code, name=row.name) for row in rows]


async def index_detail(session: AsyncSession, slug: str) -> schemas.IndexDetail | None:
    row = (
        await session.execute(select(MarketIndex).where(MarketIndex.slug == slug))
    ).scalar_one_or_none()
    if row is None:
        return None
    last = (
        await session.execute(
            select(IndexDaily.value, IndexDaily.change_pct, IndexDaily.date)
            .where(IndexDaily.slug == slug)
            .order_by(IndexDaily.date.desc())
            .limit(1)
        )
    ).first()
    source = await repository.source_ref(session, "b3", document="Índices B3")
    return schemas.IndexDetail(
        source=source,
        slug=row.slug,
        b3_code=row.b3_code,
        name=row.name,
        description=row.description,
        rebalance_note=row.rebalance_note,
        value=last[0] if last else None,
        change_percent=last[1] if last else None,
        date=last[2] if last else None,
        missing_reasons={} if last else {"value": "fechamento do índice ainda não carregado"},
    )


async def index_composition(
    session: AsyncSession, slug: str, *, reference: dt.date | None = None
) -> schemas.IndexCompositionResult | None:
    """Carteira teórica vigente. **A data é parte do dado** e vai na resposta."""
    day = (
        reference
        or (
            await session.execute(
                select(func.max(IndexComposition.date)).where(IndexComposition.slug == slug)
            )
        ).scalar()
    )
    if day is None:
        return None

    rows = (
        await session.execute(
            select(
                IndexComposition.ticker,
                IndexComposition.weight,
                IndexComposition.theoretical_qty,
                Security.company_name,
            )
            .outerjoin(Security, Security.ticker == IndexComposition.ticker)
            .where(IndexComposition.slug == slug, IndexComposition.date == day)
            .order_by(IndexComposition.weight.desc().nulls_last())
        )
    ).all()
    source = await repository.source_ref(session, "b3", document=f"carteira de {day:%d/%m/%Y}")
    return schemas.IndexCompositionResult(
        source=source,
        slug=slug,
        reference_date=day,
        members=[
            schemas.IndexMember(
                ticker=row[0],
                company_name=row[3],
                weight=row[1],
                theoretical_qty=row[2],
            )
            for row in rows
        ],
    )


async def index_history(
    session: AsyncSession, slug: str, *, days: int = 365
) -> list[schemas.IndexPoint]:
    rows = (
        await session.execute(
            select(IndexDaily.date, IndexDaily.value, IndexDaily.change_pct)
            .where(IndexDaily.slug == slug, IndexDaily.date >= dt.date.today() - dt.timedelta(days))
            .order_by(IndexDaily.date)
        )
    ).all()
    return [schemas.IndexPoint(date=row[0], value=row[1], change_percent=row[2]) for row in rows]


# --- Tesouro ----------------------------------------------------------------


async def treasury(session: AsyncSession) -> list[schemas.TreasuryBondItem]:
    """Títulos do Tesouro com a taxa e o preço do último dia disponível.

    Fonte ODbL: sai no ar sem a licença da B3 (ADR-017) — é a única página de preço
    que não depende dela.
    """
    latest = (await session.execute(select(func.max(TreasuryDaily.date)))).scalar()
    rows = (
        await session.execute(
            select(TreasuryBond, TreasuryDaily)
            .outerjoin(
                TreasuryDaily,
                (TreasuryDaily.slug == TreasuryBond.slug) & (TreasuryDaily.date == latest),
            )
            .order_by(TreasuryBond.index_type, TreasuryBond.maturity)
        )
    ).all()
    source = await repository.source_ref(session, "tesouro", document="Tesouro Transparente")
    return [
        schemas.TreasuryBondItem(
            source=source,
            slug=bond.slug,
            name=bond.name,
            index_type=bond.index_type,
            maturity=bond.maturity,
            coupon=bond.coupon,
            date=daily.date if daily else None,
            buy_rate=daily.buy_rate if daily else None,
            sell_rate=daily.sell_rate if daily else None,
            buy_price=daily.buy_price if daily else None,
            sell_price=daily.sell_price if daily else None,
            missing_reasons={} if daily else {"buy_rate": "sem cotação do título nesta data"},
        )
        for bond, daily in rows
    ]


async def treasury_history(
    session: AsyncSession, slug: str, *, days: int = 365
) -> list[schemas.TreasuryPoint]:
    rows = (
        await session.execute(
            select(
                TreasuryDaily.date,
                TreasuryDaily.buy_rate,
                TreasuryDaily.sell_rate,
                TreasuryDaily.buy_price,
                TreasuryDaily.sell_price,
            )
            .where(
                TreasuryDaily.slug == slug,
                TreasuryDaily.date >= dt.date.today() - dt.timedelta(days),
            )
            .order_by(TreasuryDaily.date)
        )
    ).all()
    return [
        schemas.TreasuryPoint(
            date=row[0],
            buy_rate=row[1],
            sell_rate=row[2],
            buy_price=row[3],
            sell_price=row[4],
        )
        for row in rows
    ]


# --- cripto -----------------------------------------------------------------


async def crypto_list(session: AsyncSession, *, limit: int = 50) -> list[schemas.CryptoItem]:
    rows = (
        (
            await session.execute(
                select(CryptoAsset).order_by(CryptoAsset.market_cap_rank.nulls_last()).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    source = await repository.source_ref(session, "coingecko")
    items: list[schemas.CryptoItem] = []
    for asset in rows:
        metric = (
            await session.execute(
                select(CryptoMetric)
                .where(CryptoMetric.id == asset.id)
                .order_by(CryptoMetric.captured_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        items.append(
            schemas.CryptoItem(
                source=source,
                id=asset.id,
                symbol=asset.symbol,
                name=asset.name,
                rank=asset.market_cap_rank,
                price=metric.price_brl if metric else None,
                change_24h=metric.change_24h if metric else None,
                market_cap=metric.market_cap_brl if metric else None,
                volume_24h=metric.volume_24h_brl if metric else None,
                missing_reasons={} if metric else {"price": "sem cotação carregada"},
            )
        )
    return items


async def crypto_history(
    session: AsyncSession, asset_id: str, *, days: int = 365
) -> list[schemas.CryptoPoint]:
    rows = (
        await session.execute(
            select(CryptoDaily.date, CryptoDaily.price_brl, CryptoDaily.volume_brl)
            .where(
                CryptoDaily.id == asset_id,
                CryptoDaily.date >= dt.date.today() - dt.timedelta(days),
            )
            .order_by(CryptoDaily.date)
        )
    ).all()
    return [schemas.CryptoPoint(date=row[0], price=row[1], volume=row[2]) for row in rows]


# --- cotações para o app ----------------------------------------------------


async def quotes(session: AsyncSession, symbols: list[str]) -> list[schemas.QuoteItem]:
    """Cotação atual de vários papéis — usado pelo app ao valorizar a carteira.

    Símbolo desconhecido volta na lista com `price = null` e motivo, em vez de sumir:
    o app precisa saber que perguntou por um papel que não existe no nosso cadastro.
    """
    codes = [s.strip().upper() for s in symbols if s.strip()][:100]
    if not codes:
        return []
    latest = await _latest_quote_date(session)
    rows = (
        await session.execute(
            select(DailyQuote.ticker, DailyQuote.close, DailyQuote.date).where(
                DailyQuote.ticker.in_(codes), DailyQuote.date == latest
            )
        )
    ).all()
    encontrados = {row[0]: (row[1], row[2]) for row in rows}
    source = await repository.source_ref(session, "b3", document="COTAHIST")
    return [
        schemas.QuoteItem(
            source=source,
            ticker=code,
            price=encontrados[code][0] if code in encontrados else None,
            date=encontrados[code][1] if code in encontrados else None,
            missing_reasons={} if code in encontrados else {"price": "papel sem cotação carregada"},
        )
        for code in codes
    ]


# --- Leitura de Mercado -----------------------------------------------------

#: Ativos do snapshot semanal, na ordem do roteiro. `kind` diz de que tabela vem.
WEEKLY_SERIES: Final[tuple[tuple[str, str, str], ...]] = (
    ("ibovespa", "Ibovespa", "index"),
    ("ifix", "IFIX", "index"),
    ("bitcoin", "Bitcoin", "crypto"),
    ("ethereum", "Ethereum", "crypto"),
    ("ptax_venda", "Dólar (PTAX)", "macro"),
)

#: Pares do radar de risco. São os que o roteiro usa para falar de "o que anda junto".
WEEKLY_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("bitcoin", "ibovespa"),
    ("bitcoin", "ptax_venda"),
    ("ethereum", "bitcoin"),
    ("ibovespa", "ptax_venda"),
    ("ibovespa", "ifix"),
)

#: Quanto histórico carregar: a maior janela (252) com folga para feriados.
WEEKLY_HISTORY_DAYS: Final = 420


async def weekly_series(session: AsyncSession, *, reference: dt.date) -> dict[str, weekly.Series]:
    """Carrega as séries do snapshot semanal das tabelas do próprio produto."""
    start = reference - dt.timedelta(days=WEEKLY_HISTORY_DAYS)
    series: dict[str, weekly.Series] = {}

    for key, label, kind in WEEKLY_SERIES:
        rows: Sequence[Row[Any]]
        if kind == "index":
            rows = (
                await session.execute(
                    select(IndexDaily.date, IndexDaily.value)
                    .where(IndexDaily.slug == key, IndexDaily.date.between(start, reference))
                    .order_by(IndexDaily.date)
                )
            ).all()
        elif kind == "crypto":
            rows = (
                await session.execute(
                    select(CryptoDaily.date, CryptoDaily.price_brl)
                    .where(CryptoDaily.id == key, CryptoDaily.date.between(start, reference))
                    .order_by(CryptoDaily.date)
                )
            ).all()
        else:
            rows = (
                await session.execute(
                    select(MacroSeries.date, MacroSeries.value)
                    .where(MacroSeries.series == key, MacroSeries.date.between(start, reference))
                    .order_by(MacroSeries.date)
                )
            ).all()

        series[key] = weekly.Series(
            key=key,
            label=label,
            points=[(row[0], Decimal(str(row[1]))) for row in rows if row[1] is not None],
            crypto=kind == "crypto",
        )
    return series


async def weekly_reading(
    session: AsyncSession, *, reference: dt.date | None = None
) -> schemas.WeeklyReading:
    """Snapshot, correlações e volatilidades da Leitura de Mercado."""
    day = reference or dt.date.today()
    series = await weekly_series(session, reference=day)
    ordered = [series[key] for key, _, _ in WEEKLY_SERIES]

    mudancas = weekly.snapshot(ordered, reference=day)
    extremos = {item.key: weekly.extremes(item, reference=day) for item in ordered}

    return schemas.WeeklyReading(
        source=await repository.source_ref(session, "b3", document=f"séries até {day:%d/%m/%Y}"),
        reference_date=day,
        snapshot=[
            schemas.WeeklyChange(
                key=change.key,
                label=change.label,
                price=change.price,
                change_7d=change.change_7d,
                change_30d=change.change_30d,
                change_ytd=change.change_ytd,
                low_52w=extremos[change.key][0],
                high_52w=extremos[change.key][1],
            )
            for change in mudancas
        ],
        correlations=[
            schemas.WeeklyCorrelation(pair=list(item.pair), windows=item.windows)
            for item in weekly.correlations(series, list(WEEKLY_PAIRS), reference=day)
        ],
        volatilities=[
            schemas.WeeklyVolatility(key=item.key, windows=item.windows)
            for item in weekly.volatilities(ordered, reference=day)
        ],
        missing_reasons={
            change.key: change.missing_reason
            for change in mudancas
            if change.missing_reason is not None
        },
    )


# --- busca global -----------------------------------------------------------

#: Grupos da busca global, na ordem em que aparecem (§2.1). `unit` entra em ações e
#: `fiagro` em FIIs — são as mesmas páginas.
ASSET_CLASSES: Final = ("stock", "fii", "etf", "bdr", "index", "treasury", "crypto")
_CLASS_OF_TYPE: Final[dict[str, str]] = {
    "stock": "stock",
    "unit": "stock",
    "fii": "fii",
    "fiagro": "fii",
    "etf": "etf",
    "bdr": "bdr",
}


async def search_assets(
    session: AsyncSession, query: str, *, per_group: int = 6
) -> schemas.AssetSearchResult:
    """Busca em todas as classes, agrupada. Ticker exato vem primeiro dentro do grupo.

    Cada grupo tem teto próprio: sem ele, "banco" devolveria vinte ações e esconderia o
    índice financeiro e os FIIs de agências que o leitor também poderia querer.
    """
    term = query.strip()
    groups: dict[str, list[schemas.AssetHit]] = {name: [] for name in ASSET_CLASSES}
    if len(term) < 2:
        return schemas.AssetSearchResult(query=term, groups=[])

    for item in await repository.search(session, term, limit=per_group * 4):
        group = groups.get(_CLASS_OF_TYPE.get(item.type, ""))
        if group is not None and len(group) < per_group:
            group.append(
                schemas.AssetHit(
                    type=item.type,
                    code=item.ticker,
                    name=item.trade_name or item.company_name,
                    price=item.price,
                )
            )

    like = f"%{term.lower()}%"
    indices = (
        await session.execute(
            select(MarketIndex)
            .where(
                or_(
                    func.lower(MarketIndex.name).like(like),
                    func.lower(MarketIndex.b3_code).like(like),
                    MarketIndex.slug.like(like),
                )
            )
            .order_by((func.lower(MarketIndex.b3_code) == term.lower()).desc(), MarketIndex.name)
            .limit(per_group)
        )
    ).scalars()
    groups["index"] = [
        schemas.AssetHit(type="index", code=row.slug, name=row.name) for row in indices
    ]

    bonds = (
        await session.execute(
            select(TreasuryBond)
            .where(func.lower(TreasuryBond.name).like(like))
            .order_by(TreasuryBond.maturity)
            .limit(per_group)
        )
    ).scalars()
    groups["treasury"] = [
        schemas.AssetHit(type="treasury", code=row.slug, name=row.name) for row in bonds
    ]

    coins = (
        await session.execute(
            select(CryptoAsset)
            .where(
                or_(
                    func.lower(CryptoAsset.name).like(like),
                    func.lower(CryptoAsset.symbol) == term.lower(),
                )
            )
            .order_by(CryptoAsset.market_cap_rank.nulls_last())
            .limit(per_group)
        )
    ).scalars()
    groups["crypto"] = [
        schemas.AssetHit(type="crypto", code=row.id, name=f"{row.name} ({row.symbol.upper()})")
        for row in coins
    ]

    return schemas.AssetSearchResult(
        query=term,
        groups=[
            schemas.AssetSearchGroup(asset_class=name, items=groups[name])
            for name in ASSET_CLASSES
            if groups[name]
        ],
    )
