"""Proventos e eventos corporativos anunciados (B3).

Alimenta a aba Eventos da página do ativo, a `/agenda` e — o mais delicado — o fator de
ajuste do histórico. Um provento que não entra aqui é uma queda inexplicada no gráfico.

O job percorre os **emissores** um a um (a B3 não tem endpoint "todos os eventos do
dia"; uma chamada por emissor traz os eventos de PETR3 e PETR4 juntos, separados pelo
ISIN), então é o mais lento do pipeline: roda uma vez por dia e falha de um emissor não
interrompe os outros. Emissor sem evento não é erro.

Dedupe: a chave natural de `corporate_actions` é (ticker, kind, ex_date, valor), então
reprocessar não duplica nem quando o mesmo provento também vem pela CVM.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date
from decimal import Decimal

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
        isin_to_ticker = _isin_map(ctx)
        alvos = tickers or sorted(isin_to_ticker.values())
        # O emissor são as quatro primeiras letras do ticker (PETR4 → PETR, MXRF11 → MXRF).
        emissores = sorted({ticker[:4] for ticker in alvos})
        falhas = 0
        for emissor in emissores:
            try:
                events = b3_events.fetch_issuer_events(emissor, isin_to_ticker)
            except SourceError as error:
                falhas += 1
                logger.warning("eventos de %s indisponíveis: %s", emissor, error)
                continue
            ctx.wrote(save(ctx, events))
        ctx.notes["emissores"] = len(emissores)
        ctx.notes["emissores_com_falha"] = falhas


#: Escala de `corporate_actions.value_per_share` (numeric(18,6)). A B3 publica até 11
#: casas; a chave de dedupe tem de ser a do banco, senão dois valores que só diferem
#: depois da 6ª casa passam aqui e colidem lá.
VALUE_SCALE = Decimal("0.000001")


def save(ctx: base.JobContext, events: list[b3_events.CorporateEvent]) -> int:
    """Grava pela chave natural, sem repetir a chave no mesmo lote (o upsert não aceita)."""
    unique: dict[tuple[object, ...], b3_events.CorporateEvent] = {}
    for event in events:
        value = (
            event.value_per_share.quantize(VALUE_SCALE)
            if event.value_per_share is not None
            else None
        )
        event = replace(event, value_per_share=value)
        unique[(event.ticker, event.kind, event.ex_date, value)] = event
    return upsert(
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
            for event in unique.values()
        ],
        conflict=["ticker", "kind", "ex_date", "value_per_share"],
        update=["record_date", "payment_date", "ratio", "source"],
    )


def _isin_map(ctx: base.JobContext) -> dict[str, str]:
    """ISIN → ticker dos papéis ativos das classes que pagam provento."""
    rows = ctx.session.execute(
        select(Security.isin, Security.ticker).where(
            Security.type.in_(KINDS_WITH_EVENTS),
            Security.status == "active",
            Security.isin.is_not(None),
        )
    )
    return {isin: ticker for isin, ticker in rows if isin}


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
