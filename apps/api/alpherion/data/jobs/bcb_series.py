"""Séries macro do Banco Central (SGS): Selic, CDI, IPCA, IGP-M e PTAX.

Fonte liberada (dados abertos). Alimenta a faixa do header, o `/mercado` e a comparação
da carteira com CDI e IPCA no engine.

Série que falha não derruba as outras: uma indisponibilidade do SGS não pode deixar a
faixa inteira sem número. O erro de cada série vai para o log e o job termina com o que
conseguiu — a contagem em `etl_runs` mostra a diferença.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from alpherion.data.jobs import base
from alpherion.data.sources import bcb
from alpherion.data.sources.http import SourceError
from alpherion.db.models import MacroSeries
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "bcb_series"
SOURCE = "bcb"
#: O SGS revisa valor publicado (IPCA sobretudo); reler o último mês é barato.
DEFAULT_WINDOW_DAYS = 45


def run(*, since: date | None = None, full: bool = False) -> None:
    start = None if full else (since or date.today() - timedelta(days=DEFAULT_WINDOW_DAYS))
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        falhas: list[str] = []
        for series in bcb.SERIES:
            try:
                points = bcb.fetch(series, start=start)
            except SourceError as error:
                falhas.append(series)
                logger.warning("SGS %s indisponível: %s", series, error)
                continue
            ctx.wrote(
                upsert(
                    ctx.session,
                    MacroSeries,
                    [{"series": p.series, "date": p.date, "value": p.value} for p in points],
                )
            )
        if falhas:
            ctx.notes["series_com_falha"] = falhas


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
