"""Proventos e eventos corporativos anunciados (B3).

Alimenta a aba Eventos da página do ativo, a `/agenda` e — o mais delicado — o fator de
ajuste do histórico. Um provento que não entra aqui é uma queda inexplicada no gráfico.

O job percorre os papéis ativos um a um (a B3 não tem endpoint "todos os eventos do
dia"), então é o mais lento do pipeline: roda uma vez por dia e falha de um papel não
interrompe os outros. Papel sem evento não é erro — a maioria das empresas não anuncia
nada num dia qualquer.

Dedupe: a chave natural de `corporate_actions` é (ticker, kind, ex_date, valor), então
reprocessar não duplica nem quando o mesmo provento também vem pela CVM.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.sources import b3_events
from alpherion.data.sources.http import SourceError
from alpherion.db.models import CorporateAction, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "b3_corporate_actions"
SOURCE = "b3"

#: Só classes que pagam provento; ETF e BDR distribuem por outra via (v1.x).
KINDS_WITH_EVENTS = ("stock", "unit", "fii", "fiagro")


def run(*, tickers: list[str] | None = None) -> None:
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        alvos = tickers or _active_tickers(ctx)
        falhas = 0
        for ticker in alvos:
            try:
                events = b3_events.fetch_events(ticker)
            except SourceError as error:
                falhas += 1
                logger.warning("eventos de %s indisponíveis: %s", ticker, error)
                continue
            ctx.wrote(
                upsert(
                    ctx.session,
                    CorporateAction,
                    [
                        {
                            "ticker": event.ticker,
                            "kind": event.kind,
                            "ex_date": event.ex_date,
                            "record_date": event.record_date,
                            "payment_date": event.payment_date,
                            "value_per_share": event.value_per_share,
                            "ratio": event.ratio,
                            "source": event.source,
                        }
                        for event in events
                    ],
                    conflict=["ticker", "kind", "ex_date", "value_per_share"],
                    update=["record_date", "payment_date", "ratio", "source"],
                )
            )
        ctx.notes["papeis"] = len(alvos)
        ctx.notes["papeis_com_falha"] = falhas


def _active_tickers(ctx: base.JobContext) -> list[str]:
    rows = ctx.session.execute(
        select(Security.ticker)
        .where(Security.type.in_(KINDS_WITH_EVENTS), Security.status == "active")
        .order_by(Security.ticker)
    )
    return [ticker for (ticker,) in rows]


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
