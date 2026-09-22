"""Recalcula o fator de ajuste e o fechamento ajustado de `daily_quotes`.

Roda **depois** de `b3_corporate_actions`: um provento novo muda o fator de todo o
histórico anterior àquela data. Não é carga de fonte — só lê o banco e regrava duas
colunas, então não depende de licença para rodar (o que depende é exibir o preço).

O recálculo é por papel e do zero: acumular incrementalmente exigiria saber exatamente
quais eventos já foram aplicados, e um evento contado duas vezes deforma a série inteira
sem deixar rastro. Refazer do zero é lento e é certo — e é o que torna o reprocessamento
depois de uma correção de evento uma operação sem risco.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.transform.adjust import Event, adjust
from alpherion.db.models import CorporateAction, DailyQuote, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "adjust_factors"
#: Classes cujo histórico é ajustado; índice e Tesouro não têm provento por papel.
ADJUSTABLE = ("stock", "unit", "fii", "fiagro", "etf", "bdr")


def run(*, tickers: list[str] | None = None) -> None:
    with base.run(JOB, period=date.today()) as ctx:
        alvos = tickers or _adjustable_tickers(ctx)
        ajustados = 0
        for ticker in alvos:
            quotes = _closes(ctx, ticker)
            if not quotes:
                continue
            series = adjust(quotes, _events(ctx, ticker))
            ctx.wrote(
                upsert(
                    ctx.session,
                    DailyQuote,
                    [
                        {
                            "ticker": ticker,
                            "date": item.date,
                            "close": item.close,
                            "adj_factor": item.adj_factor,
                            "close_adjusted": item.close_adjusted,
                        }
                        for item in series
                    ],
                    update=["adj_factor", "close_adjusted"],
                )
            )
            ajustados += 1
        ctx.notes["papeis_ajustados"] = ajustados


def _adjustable_tickers(ctx: base.JobContext) -> list[str]:
    rows = ctx.session.execute(
        select(Security.ticker).where(Security.type.in_(ADJUSTABLE)).order_by(Security.ticker)
    )
    return [ticker for (ticker,) in rows]


def _closes(ctx: base.JobContext, ticker: str) -> list[tuple[date, Decimal]]:
    rows = ctx.session.execute(
        select(DailyQuote.date, DailyQuote.close)
        .where(DailyQuote.ticker == ticker)
        .order_by(DailyQuote.date)
    ).all()
    return [(row[0], Decimal(str(row[1]))) for row in rows if row[1] is not None]


def _events(ctx: base.JobContext, ticker: str) -> list[Event]:
    rows = ctx.session.execute(
        select(
            CorporateAction.ex_date,
            CorporateAction.kind,
            CorporateAction.value_per_share,
            CorporateAction.ratio,
        ).where(CorporateAction.ticker == ticker, CorporateAction.ex_date.is_not(None))
    )
    return [
        Event(ex_date=ex_date, kind=kind, value_per_share=value, ratio=ratio)
        for ex_date, kind, value, ratio in rows
        if ex_date is not None
    ]


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
