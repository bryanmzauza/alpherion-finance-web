"""Comunicados entregues à CVM (IPE) — metadados e link, nunca o documento.

Fonte liberada. Alimenta a aba Comunicados da página do ativo, a tab Eventos de
`/mercado` e a `/agenda`.

Carga **incremental por data de entrega**: o job olha o documento mais recente já
carregado e relê a partir de alguns dias antes, porque uma entrega pode aparecer no
arquivo depois da data (protocolo em análise). O `protocol` é a chave natural, então
reler é gratuito — o upsert não duplica.

Site.md §8.3: o texto do documento não é baixado nem resumido. Resumir fato relevante é
interpretação, e interpretação é análise (Res. CVM 20).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import func, select

from alpherion.data.jobs import base
from alpherion.data.sources import cvm_documents
from alpherion.db.models import CompanyDocument, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "cvm_documents"
SOURCE = "cvm_ipe"
#: Margem para trás na carga incremental: entregas atrasam na publicação do arquivo.
OVERLAP_DAYS = 7


def run(*, year: int | None = None, since: date | None = None, full: bool = False) -> None:
    target = year or date.today().year
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        start = None if full else (since or _last_loaded(ctx))
        documents = cvm_documents.fetch_year(target, since=start)

        # O ticker principal facilita a consulta da página do ativo; documento de
        # companhia sem papel listado entra do mesmo jeito, só sem ticker.
        tickers = _main_tickers(ctx)
        ctx.wrote(
            upsert(
                ctx.session,
                CompanyDocument,
                [
                    {
                        "protocol": doc.protocol,
                        "cvm_code": doc.cvm_code,
                        "ticker": tickers.get(doc.cvm_code),
                        "category": doc.category,
                        "type": doc.type,
                        "subject": doc.subject,
                        "delivered_at": doc.delivered_at,
                        "reference_date": doc.reference_date,
                        "url": doc.url,
                    }
                    for doc in documents
                ],
            )
        )
        ctx.notes["desde"] = start.isoformat() if start else "ano inteiro"


def _last_loaded(ctx: base.JobContext) -> date:
    """Data de entrega mais recente no banco, menos a margem."""
    latest = ctx.session.execute(select(func.max(CompanyDocument.delivered_at))).scalar()
    if latest is None:
        return date(date.today().year, 1, 1)
    return latest - timedelta(days=OVERLAP_DAYS)


def _main_tickers(ctx: base.JobContext) -> dict[int, str]:
    """Um ticker por `cvm_code` — o menor, que é o ordinário (PETR3 antes de PETR4).

    Só papel **ativo**: um código antigo que ficou no cadastro como `inactive` não pode
    ser o ticker do comunicado de hoje.
    """
    rows = ctx.session.execute(
        select(Security.cvm_code, func.min(Security.ticker))
        .where(Security.cvm_code.is_not(None), Security.status == "active")
        .group_by(Security.cvm_code)
    )
    return {code: ticker for code, ticker in rows if code is not None}


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
