"""Séries temporais do Banco Central (SGS).

Dados abertos, verificados em 21/09/2026 (`docs/fontes-de-dados.md`): liberados para
produção. Alimentam a faixa do header (Selic, CDI, IPCA, dólar), o `/mercado` e o
engine (comparação da carteira com CDI e IPCA).

**Os códigos do SGS ficam todos aqui** (site.md §3.5): espalhá-los pelos jobs torna
impossível responder "de onde vem esse número" sem caçar no código.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

import httpx

from alpherion.data.sources.http import DEFAULT_TIMEOUT, USER_AGENT, SourceError, check_host

logger = logging.getLogger(__name__)

BASE_URL: Final = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

#: Série no nosso schema → código no SGS do BCB.
#: 11   Selic efetiva (taxa diária, % a.d.)
#: 432  Selic meta definida pelo Copom (% a.a.)
#: 12   CDI (taxa diária, % a.d.)
#: 433  IPCA (variação mensal, %)
#: 189  IGP-M (variação mensal, %)
#: 1    Dólar americano (venda, PTAX, diário)
#: 10813 Dólar americano (compra, PTAX, diário)
SERIES: Final[dict[str, int]] = {
    "selic": 11,
    "selic_meta": 432,
    "cdi": 12,
    "ipca": 433,
    "igpm": 189,
    "ptax_venda": 1,
    "ptax_compra": 10813,
}


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    series: str
    date: date
    value: Decimal


def _parse_point(series: str, item: dict[str, Any]) -> SeriesPoint | None:
    raw_date = str(item.get("data", "")).strip()
    raw_value = str(item.get("valor", "")).strip()
    if not raw_date or not raw_value:
        return None
    try:
        value = Decimal(raw_value.replace(",", "."))
    except InvalidOperation:
        logger.warning("SGS %s: valor não numérico em %s: %r", series, raw_date, raw_value)
        return None
    return SeriesPoint(
        series=series,
        date=datetime.strptime(raw_date, "%d/%m/%Y").date(),
        value=value,
    )


def fetch(
    series: str,
    *,
    start: date | None = None,
    end: date | None = None,
    http: httpx.Client | None = None,
) -> list[SeriesPoint]:
    """Baixa uma série do SGS.

    Sem `start`, o BCB devolve a série inteira — que para o CDI são ~15 mil pontos.
    O job diário sempre passa um intervalo curto; o backfill é que pede tudo.
    """
    if series not in SERIES:
        raise SourceError(f"série desconhecida: {series!r} (ver SERIES em sources/bcb.py)")

    url = BASE_URL.format(code=SERIES[series])
    check_host(url)
    params: dict[str, str] = {"formato": "json"}
    if start:
        params["dataInicial"] = f"{start:%d/%m/%Y}"
    if end:
        params["dataFinal"] = f"{end:%d/%m/%Y}"

    def _get(session: httpx.Client) -> httpx.Response:
        return session.get(url, params=params)

    if http is not None:
        response = _get(http)
    else:
        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT}) as session:
            response = _get(session)

    if response.status_code != httpx.codes.OK:
        raise SourceError(f"SGS {series}: HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as error:
        # O SGS responde HTML quando está fora do ar — não deixar virar "série vazia".
        raise SourceError(f"SGS {series}: resposta não é JSON") from error
    if not isinstance(payload, list):
        raise SourceError(f"SGS {series}: formato inesperado")

    points = [p for item in payload if (p := _parse_point(series, item)) is not None]
    logger.info("SGS %s (código %d): %d pontos", series, SERIES[series], len(points))
    return points


def fetch_all(
    *, start: date | None = None, http: httpx.Client | None = None
) -> Iterator[SeriesPoint]:
    """Todas as séries que o produto usa, na ordem de `SERIES`."""
    for series in SERIES:
        yield from fetch(series, start=start, http=http)
