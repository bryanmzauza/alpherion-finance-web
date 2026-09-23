"""Séries temporais do Banco Central (SGS).

Dados abertos, verificados em 21/09/2026 (`docs/fontes-de-dados.md`): liberados para
produção. Alimentam a faixa do header (Selic, CDI, IPCA, dólar), o `/mercado` e o
engine (comparação da carteira com CDI e IPCA).

**Os códigos do SGS ficam todos aqui** (site.md §3.5): espalhá-los pelos jobs torna
impossível responder "de onde vem esse número" sem caçar no código.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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


#: Séries de periodicidade **diária**. Desde 2025 o SGS recusa (HTTP 406) consulta de
#: série diária sem datas ou com janela de mais de 10 anos; a série inteira sai em
#: pedaços. As mensais (IPCA, IGP-M) continuam numa chamada só.
DAILY_SERIES: Final = frozenset({"selic", "selic_meta", "cdi", "ptax_venda", "ptax_compra"})

#: Maior janela aceita pelo SGS para série diária ("no máximo, 10 anos"), com folga.
MAX_DAILY_WINDOW: Final = timedelta(days=3650 - 2)

#: Começo da carga completa das séries diárias: o CDI começa em 1986 e é a mais antiga
#: que o produto usa. Janela anterior ao início de uma série responde 404 — "ainda não
#: existia", não erro.
DAILY_HISTORY_START: Final = date(1986, 1, 1)

#: Esperas entre tentativas de uma janela. O SGS devolve, de vez em quando, uma página
#: de erro em HTML (status 200) ou 5xx para uma janela que responde normal segundos
#: depois; sem nova tentativa, a série perderia dez anos por um soluço do servidor.
#: Na carga completa de 23/09/2026 o SGS ficou mais de 17 s respondendo 502 para a PTAX
#: de compra; as esperas cobrem pouco mais de 1,5 min antes de desistir da janela.
RETRY_DELAYS: tuple[float, ...] = (3.0, 10.0, 30.0, 60.0)


class _TransientError(SourceError):
    """Falha que costuma passar sozinha: HTML no lugar do JSON, 5xx."""


def windows(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Janelas consecutivas de no máximo `MAX_DAILY_WINDOW`, cobrindo [start, end]."""
    cursor = start
    while cursor <= end:
        stop = min(cursor + MAX_DAILY_WINDOW, end)
        yield cursor, stop
        cursor = stop + timedelta(days=1)


def fetch(
    series: str,
    *,
    start: date | None = None,
    end: date | None = None,
    http: httpx.Client | None = None,
) -> list[SeriesPoint]:
    """Baixa uma série do SGS.

    Sem `start`, vem a série inteira — para série diária, em janelas de até 10 anos
    (exigência do SGS). O job diário sempre passa um intervalo curto; o backfill é que
    pede tudo.
    """
    if series not in SERIES:
        raise SourceError(f"série desconhecida: {series!r} (ver SERIES em sources/bcb.py)")

    if series not in DAILY_SERIES:
        points = _fetch_window(series, start, end, http=http)
    else:
        first = start or DAILY_HISTORY_START
        last = end or date.today()
        points = []
        for window_start, window_end in windows(first, last):
            points.extend(
                _fetch_window(series, window_start, window_end, http=http, missing_ok=start is None)
            )
    logger.info("SGS %s (código %d): %d pontos", series, SERIES[series], len(points))
    return points


def _fetch_window(
    series: str,
    start: date | None,
    end: date | None,
    *,
    http: httpx.Client | None,
    missing_ok: bool = False,
) -> list[SeriesPoint]:
    url = BASE_URL.format(code=SERIES[series])
    check_host(url)
    params: dict[str, str] = {"formato": "json"}
    if start:
        params["dataInicial"] = f"{start:%d/%m/%Y}"
    if end:
        params["dataFinal"] = f"{end:%d/%m/%Y}"

    def _get(session: httpx.Client) -> httpx.Response:
        return session.get(url, params=params, headers={"Accept": "application/json"})

    def _attempt() -> list[Any] | None:
        """Uma tentativa: a lista da resposta, `None` se 404 aceitável, ou exceção."""
        if http is not None:
            response = _get(http)
        else:
            with httpx.Client(
                timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT}
            ) as session:
                response = _get(session)

        if response.status_code == httpx.codes.NOT_FOUND and missing_ok:
            return None  # janela anterior ao começo da série
        if response.status_code != httpx.codes.OK:
            raise _TransientError(f"SGS {series}: HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as error:
            # O SGS responde HTML quando está fora do ar — não deixar virar "série vazia".
            raise _TransientError(f"SGS {series}: resposta não é JSON") from error
        if not isinstance(payload, list):
            raise SourceError(f"SGS {series}: formato inesperado")
        return payload

    for delay in (*RETRY_DELAYS, None):
        try:
            payload = _attempt()
            break
        except _TransientError as error:
            if delay is None:
                raise SourceError(str(error)) from error
            logger.info("%s — nova tentativa em %.0f s", error, delay)
            time.sleep(delay)
    if payload is None:
        return []

    return [p for item in payload if (p := _parse_point(series, item)) is not None]


def fetch_all(
    *, start: date | None = None, http: httpx.Client | None = None
) -> Iterator[SeriesPoint]:
    """Todas as séries que o produto usa, na ordem de `SERIES`."""
    for series in SERIES:
        yield from fetch(series, start=start, http=http)
