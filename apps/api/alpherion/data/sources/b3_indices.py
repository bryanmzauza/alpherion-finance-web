"""Índices da B3: carteira teórica e fechamento diário.

Alimenta `/indices/[slug]` (com a composição datada), a faixa do header e o campo
`etf_index_slug` dos ETFs. Nove índices no v1.0 — os que o investidor pessoa física
acompanha e que aparecem no portal.

**A carteira teórica é datada e a data é parte do dado.** A B3 rebalanceia a cada
quadrimestre e publica prévias; a página precisa dizer "carteira de 02/09/2026", não
"composição do Ibovespa". Quando o endpoint falha, o job **mantém a última carteira** e
a página continua mostrando a data dela — nunca uma lista vazia, nunca uma lista velha
sem dizer que é velha (§3.2 do plano).

ADR-017: composição e fechamento de índice são dado da B3; a publicação depende da
licença (`MARKET_B3_PRICES_ENABLED`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

import httpx

from alpherion.data.sources.b3_api import (
    LISTED_BASE,
    B3UnavailableError,
    build_url,
    fetch_json,
    fetch_pages,
    field,
)

logger = logging.getLogger(__name__)

#: Os dois proxies ficam no host da listagem (o "sistemaswebb3-indices" nunca existiu no
#: DNS — era por isso que o job falhava com `getaddrinfo`).
PORTFOLIO_PATH: Final = "indexProxy/indexCall/GetPortfolioDay"
#: Fechamentos de um ano, em grade dia × mês — é o que a página "Estatísticas
#: históricas" da B3 usa.
STATISTICS_PATH: Final = "indexStatisticsProxy/IndexCall/GetPortfolioDay"

#: Slug da URL → código do índice na B3. A ordem é a do portal (§4.2 do plano).
INDICES: Final[dict[str, str]] = {
    "ibovespa": "IBOV",
    "ifix": "IFIX",
    "idiv": "IDIV",
    "smll": "SMLL",
    "ibrx-100": "IBXX",
    "ibra": "IBRA",
    "ifnc": "IFNC",
    "imob": "IMOB",
    "util": "UTIL",
}

#: `segment` do endpoint: 1 = carteira do dia, por setor de atuação.
DEFAULT_SEGMENT: Final = "1"


@dataclass(frozen=True, slots=True)
class IndexMember:
    """Um papel na carteira teórica, com o peso do dia."""

    index_slug: str
    reference_date: date
    ticker: str
    company_name: str | None
    #: Participação no índice, em fração (0,0812 = 8,12%) — nunca em percentual cru,
    #: porque a tabela e o cálculo de concentração usam fração.
    weight: Decimal | None
    theoretical_quantity: Decimal | None


def _decimal(value: Any) -> Decimal | None:
    """`8,124` e `1.234.567` → Decimal. Valor ausente vira None, nunca zero."""
    if value is None:
        return None
    text = str(value).strip().replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        logger.warning("número não reconhecido na carteira do índice: %r", value)
        return None


def _date(value: Any) -> date | None:
    text = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    return None


def parse_portfolio(
    payload: list[dict[str, Any]],
    *,
    slug: str,
    reference_date: date,
) -> list[IndexMember]:
    members: list[IndexMember] = []
    for record in payload:
        ticker = field(record, "cod", "code", "ticker")
        if not ticker:
            continue
        percentage = _decimal(field(record, "part", "participation", "percentual"))
        members.append(
            IndexMember(
                index_slug=slug,
                reference_date=reference_date,
                ticker=str(ticker).strip().upper(),
                company_name=field(record, "asset", "companyName", "nome"),
                weight=percentage / Decimal(100) if percentage is not None else None,
                theoretical_quantity=_decimal(field(record, "theoricalQty", "quantidadeTeorica")),
            )
        )
    return members


def portfolio_date(payload: Any) -> date | None:
    """Data da carteira, do cabeçalho da resposta (`"date": "23/09/26"`)."""
    header = payload.get("header") if isinstance(payload, dict) else None
    return _date(header.get("date")) if isinstance(header, dict) else None


def fetch_composition(
    slug: str,
    *,
    http: httpx.Client | None = None,
) -> list[IndexMember]:
    """Carteira teórica vigente de um índice, com a **data que a B3 informa**.

    Uma carteira vazia é sempre erro, nunca "o índice não tem papéis": gravá-la apagaria
    a composição inteira no banco e a página mostraria um índice sem ativos. Sem data no
    cabeçalho também é erro: carteira sem data é justamente o que a página não pode
    mostrar.
    """
    if slug not in INDICES:
        raise ValueError(f"índice desconhecido: {slug!r} (ver INDICES em b3_indices.py)")
    params = {"language": "pt-br", "index": INDICES[slug], "segment": DEFAULT_SEGMENT}
    first = fetch_json(
        build_url(LISTED_BASE, PORTFOLIO_PATH, {**params, "pageNumber": 1, "pageSize": 1}),
        http=http,
    )
    reference = portfolio_date(first)
    records = fetch_pages(LISTED_BASE, PORTFOLIO_PATH, params, http=http)
    if not records:
        raise B3UnavailableError(
            f"carteira do índice {slug} veio vazia — manter a última conhecida"
        )
    if reference is None:
        raise B3UnavailableError(f"carteira do índice {slug} sem data — manter a última conhecida")
    members = parse_portfolio(records, slug=slug, reference_date=reference)
    logger.info("índice %s: %d papéis na carteira de %s", slug, len(members), reference)
    return members


@dataclass(frozen=True, slots=True)
class IndexClose:
    index_slug: str
    date: date
    close: Decimal
    change_percent: Decimal | None


def parse_year_closes(payload: Any, *, slug: str, year: int) -> list[IndexClose]:
    """Grade anual da B3 (linha = dia, `rateValue1..12` = meses) → fechamentos em ordem.

    A grade não traz variação: ela é calculada depois, sobre o fechamento anterior
    (`with_changes`), porque o primeiro pregão do ano depende do último do ano anterior.
    """
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise B3UnavailableError(f"estatísticas de {slug} {year}: formato inesperado")
    closes: list[IndexClose] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = row.get("day")
        if not isinstance(day, int) or not 1 <= day <= 31:
            continue
        for month in range(1, 13):
            value = _decimal(row.get(f"rateValue{month}"))
            if value is None:
                continue
            try:
                when = date(year, month, day)
            except ValueError:
                continue
            closes.append(IndexClose(index_slug=slug, date=when, close=value, change_percent=None))
    return sorted(closes, key=lambda c: c.date)


def with_changes(closes: list[IndexClose], previous: Decimal | None = None) -> list[IndexClose]:
    """Variação de cada dia sobre o fechamento anterior, em **fração**.

    `previous` é o último fechamento antes do primeiro da lista (o de 30/12 para uma
    grade de janeiro). Sem ele, o primeiro dia fica sem variação — `None`, não zero.
    """
    result: list[IndexClose] = []
    for close in sorted(closes, key=lambda c: c.date):
        change = (close.close / previous - 1) if previous else None
        result.append(IndexClose(close.index_slug, close.date, close.close, change))
        previous = close.close
    return result


def fetch_year_closes(
    slug: str, year: int, *, http: httpx.Client | None = None
) -> list[IndexClose]:
    """Fechamentos de um índice num ano (sem variação — ver `with_changes`)."""
    if slug not in INDICES:
        raise ValueError(f"índice desconhecido: {slug!r} (ver INDICES em b3_indices.py)")
    payload = fetch_json(
        build_url(
            LISTED_BASE,
            STATISTICS_PATH,
            {"index": INDICES[slug], "language": "pt-br", "year": str(year)},
        ),
        http=http,
    )
    closes = parse_year_closes(payload, slug=slug, year=year)
    logger.info("índice %s %d: %d fechamentos", slug, year, len(closes))
    return closes
