"""Acumulado em 12 meses das séries do BCB (CDI e IPCA) para a faixa (§2.1).

O SGS publica o CDI como taxa **diária** (% a.d.) e o IPCA como variação **mensal**
(% no mês). O número que o leitor reconhece — "CDI 12 m: 10,9%", "IPCA 12 m: 4,5%" — é o
acumulado composto, e compor é conta: fica aqui, na API, e não no `web` (§2.3).

Duas regras:

- **Composto, não somado.** 12 meses de 0,9% não são 10,8%, são 11,35%.
- **Janela incompleta não vira número.** Sem cobertura dos 12 meses, a resposta é
  `None` com o motivo — um "acumulado em 12 meses" calculado sobre 7 meses seria um
  número errado com rótulo certo, o pior tipo de erro.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from decimal import Decimal
from typing import Final, NamedTuple

#: Folga no começo da janela diária: feriado ou fim de semana logo depois do início da
#: janela não pode fazer uma série completa parecer incompleta.
DAILY_START_TOLERANCE: Final = dt.timedelta(days=7)

HUNDRED: Final = Decimal(100)


class Accumulated(NamedTuple):
    """Acumulado em % (10,9 = 10,9%), a data do último ponto e, se faltou, o motivo."""

    value: Decimal | None
    as_of: dt.date | None
    reason: str | None = None


def daily_12m(points: Sequence[tuple[dt.date, Decimal]]) -> Accumulated:
    """Composição de uma taxa diária (% a.d.) nos 12 meses que terminam no último ponto."""
    if not points:
        return Accumulated(None, None, "série ainda não carregada")
    ordered = sorted(points)
    end = ordered[-1][0]
    start = _one_year_before(end)
    window = [(day, rate) for day, rate in ordered if start < day <= end]
    if not window or window[0][0] > start + DAILY_START_TOLERANCE:
        return Accumulated(None, end, "série com menos de 12 meses carregados")

    factor = Decimal(1)
    for _day, rate in window:
        factor *= 1 + rate / HUNDRED
    return Accumulated(_as_percent(factor), end)


def monthly_12m(points: Sequence[tuple[dt.date, Decimal]]) -> Accumulated:
    """Composição das 12 últimas variações mensais (% no mês), sem mês faltando."""
    if not points:
        return Accumulated(None, None, "série ainda não carregada")
    ordered = sorted(points)
    end = ordered[-1][0]
    last_12 = ordered[-12:]
    if len(last_12) < 12 or _months_between(last_12[0][0], end) != 11:
        return Accumulated(None, end, "série sem os 12 meses completos")

    factor = Decimal(1)
    for _day, rate in last_12:
        factor *= 1 + rate / HUNDRED
    return Accumulated(_as_percent(factor), end)


def _as_percent(factor: Decimal) -> Decimal:
    return ((factor - 1) * HUNDRED).quantize(Decimal("0.01"))


def _one_year_before(day: dt.date) -> dt.date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:  # 29/02
        return day.replace(year=day.year - 1, day=28)


def _months_between(first: dt.date, last: dt.date) -> int:
    return (last.year - first.year) * 12 + (last.month - first.month)
