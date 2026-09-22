"""Demonstrações financeiras da CVM (DFP anual; ITR fica para o v1.x).

Fonte liberada: os indicadores de balanço — ROE, ROIC, margens, endividamento, LPA, VPA
— saem no ar mesmo sem a licença da B3 (ADR-017), porque não dependem de preço.

O período do job é o **ano do exercício**, e é ele que torna o reprocessamento previsível:
`python -m alpherion.data.jobs.cvm_statements --ano 2025` recarrega só 2025, com a
versão mais recente de cada conta, sem tocar nos outros anos.

Carga inicial (todos os anos desde 2010) é o `backfill-market.sh`, não este job.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from alpherion.data.jobs import base
from alpherion.data.sources import cvm
from alpherion.data.transform.cvm_statements import ANNUAL, full_year_only
from alpherion.db.models import FinancialStatement
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "cvm_statements"
SOURCE = "cvm"


def run(*, year: int | None = None, period_type: str = ANNUAL) -> None:
    """Carrega a DFP de um ano. Sem `year`, o exercício mais recente publicado.

    A DFP de um exercício é entregue no primeiro trimestre do ano seguinte, então o
    padrão é o ano anterior: em setembro de 2026, a última DFP completa é a de 2025.
    """
    target = year or date.today().year - 1
    with base.run(JOB, period=date(target, 12, 31), source=SOURCE) as ctx:
        rows = cvm.fetch_statements(target, period_type=period_type)
        selected = list(full_year_only(rows)) if period_type == ANNUAL else rows
        ctx.wrote(
            upsert(
                ctx.session,
                FinancialStatement,
                [
                    {
                        "cvm_code": row.cvm_code,
                        "period_end": row.period_end,
                        "period_type": row.period_type,
                        "statement": row.statement,
                        "consolidated": row.consolidated,
                        "account_code": row.account_code,
                        "account_name": row.account_name,
                        "value": row.value,
                        "version": row.version,
                    }
                    for row in selected
                ],
            )
        )
        ctx.notes["linhas_descartadas"] = len(rows) - len(selected)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Carrega a DFP de um exercício.")
    parser.add_argument("--ano", type=int, default=None, help="exercício (padrão: o anterior)")
    args = parser.parse_args()
    run(year=args.ano)


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(_cli)
