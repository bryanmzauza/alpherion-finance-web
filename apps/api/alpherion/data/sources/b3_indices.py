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

from alpherion.data.sources.b3_api import INDICES_BASE, B3UnavailableError, fetch_pages, field

logger = logging.getLogger(__name__)

PORTFOLIO_PATH: Final = "indexProxy/indexCall/GetPortfolioDay"
INDEX_STATISTICS_PATH: Final = "indexProxy/indexCall/GetIndexStatistics"

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


def fetch_composition(
    slug: str,
    *,
    reference_date: date | None = None,
    http: httpx.Client | None = None,
) -> list[IndexMember]:
    """Carteira teórica vigente de um índice.

    Uma carteira vazia é sempre erro, nunca "o índice não tem papéis": gravá-la apagaria
    a composição inteira no banco e a página mostraria um índice sem ativos.
    """
    if slug not in INDICES:
        raise ValueError(f"índice desconhecido: {slug!r} (ver INDICES em b3_indices.py)")
    records = fetch_pages(
        INDICES_BASE,
        PORTFOLIO_PATH,
        {"language": "pt-br", "index": INDICES[slug], "segment": DEFAULT_SEGMENT},
        http=http,
    )
    members = parse_portfolio(records, slug=slug, reference_date=reference_date or date.today())
    if not members:
        raise B3UnavailableError(
            f"carteira do índice {slug} veio vazia — manter a última conhecida"
        )
    logger.info(
        "índice %s: %d papéis na carteira de %s", slug, len(members), members[0].reference_date
    )
    return members


@dataclass(frozen=True, slots=True)
class IndexClose:
    index_slug: str
    date: date
    close: Decimal
    change_percent: Decimal | None


def parse_statistics(payload: Any, *, slug: str) -> list[IndexClose]:
    """Fechamentos do endpoint de estatísticas do índice."""
    records = payload if isinstance(payload, list) else [payload]
    closes: list[IndexClose] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        day = _date(field(record, "date", "data", "day"))
        value = _decimal(field(record, "value", "valor", "close"))
        if day is None or value is None:
            continue
        closes.append(
            IndexClose(
                index_slug=slug,
                date=day,
                close=value,
                change_percent=_decimal(field(record, "variation", "variacao")),
            )
        )
    return closes
