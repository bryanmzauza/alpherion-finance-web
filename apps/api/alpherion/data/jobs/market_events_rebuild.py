"""Reconstrói a agenda (`market_events`).

Roda depois de `b3_corporate_actions` e `cvm_documents`, e antes de `revalidate_pages`:
é o que faz `/agenda` e a tab Eventos de `/mercado` mostrarem o dia de hoje.

A janela é deliberadamente curta em torno de hoje (um ano para trás, um para frente):
a agenda serve para "o que aconteceu e o que vem", e reconstruir a série histórica
inteira todo dia custaria minutos para nenhum ganho. O reprocessamento de um período
antigo é o mesmo job com `--desde`/`--ate`.

Ids determinísticos (`transform/events.py`) tornam o rebuild idempotente: o mesmo
provento gera o mesmo par de eventos, sem duplicar e sem trocar de id.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.transform import events as build_events
from alpherion.db.models import CompanyDocument, CorporateAction, MarketEvent
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "market_events_rebuild"

PAST_DAYS = 365
FUTURE_DAYS = 365


def run(*, since: date | None = None, until: date | None = None) -> None:
    today = date.today()
    start = since or today - timedelta(days=PAST_DAYS)
    end = until or today + timedelta(days=FUTURE_DAYS)

    with base.run(JOB, period=today) as ctx:
        rows = build_events.build(
            _actions(ctx, start, end),
            _documents(ctx, start, end),
        )
        # Um evento macro de outro ano no arquivo não deve entrar fora da janela.
        window = [row for row in rows if start <= row.date <= end]
        ctx.wrote(
            upsert(
                ctx.session,
                MarketEvent,
                [
                    {
                        "id": row.id,
                        "kind": row.kind,
                        "date": row.date,
                        "ticker": row.ticker,
                        "cvm_code": row.cvm_code,
                        "title": row.title,
                        "payload": row.payload,
                        "source": row.source,
                    }
                    for row in window
                ],
            )
        )
        ctx.notes["janela"] = f"{start.isoformat()}..{end.isoformat()}"


def _actions(
    ctx: base.JobContext, start: date, end: date
) -> list[build_events.CorporateActionInput]:
    rows = ctx.session.execute(
        select(
            CorporateAction.id,
            CorporateAction.ticker,
            CorporateAction.kind,
            CorporateAction.ex_date,
            CorporateAction.payment_date,
            CorporateAction.value_per_share,
            CorporateAction.ratio,
            CorporateAction.source,
        ).where(
            # Basta uma das duas datas cair na janela: um provento anunciado com data-com
            # em dezembro e pagamento em janeiro aparece nos dois lugares certos.
            (CorporateAction.ex_date.between(start, end))
            | (CorporateAction.payment_date.between(start, end))
        )
    ).all()
    return [
        build_events.CorporateActionInput(
            id=row[0],
            ticker=row[1],
            kind=row[2],
            ex_date=row[3],
            payment_date=row[4],
            value_per_share=Decimal(str(row[5])) if row[5] is not None else None,
            ratio=row[6],
            source=row[7],
        )
        for row in rows
    ]


def _documents(ctx: base.JobContext, start: date, end: date) -> list[build_events.DocumentInput]:
    rows = ctx.session.execute(
        select(
            CompanyDocument.protocol,
            CompanyDocument.cvm_code,
            CompanyDocument.ticker,
            CompanyDocument.category,
            CompanyDocument.subject,
            CompanyDocument.delivered_at,
        ).where(CompanyDocument.delivered_at.between(start, end))
    ).all()
    return [
        build_events.DocumentInput(
            protocol=row[0],
            cvm_code=row[1],
            ticker=row[2],
            category=row[3],
            subject=row[4],
            delivered_at=row[5],
        )
        for row in rows
    ]


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Reconstrói a agenda de eventos.")
    parser.add_argument("--desde", default=None, help="aaaa-mm-dd")
    parser.add_argument("--ate", default=None, help="aaaa-mm-dd")
    args = parser.parse_args()
    run(since=_parse(args.desde), until=_parse(args.ate))


def _parse(value: str | None) -> date | None:
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(_cli)
