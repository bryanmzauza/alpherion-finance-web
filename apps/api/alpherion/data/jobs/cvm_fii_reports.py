"""Informes mensais dos fundos imobiliários (CVM).

Fonte liberada. Dá a `/fiis/[ticker]` patrimônio, valor patrimonial da cota, número de
cotistas, taxa de administração e — quando o fundo informa — vacância. O P/VP do FII sai
daqui (`nav_per_share`), não do balanço.

O informe é por **CNPJ**; `fii_reports` é por ticker. A conversão é feita aqui, com o
cadastro de `securities`: informe de fundo que não está listado é ignorado (não existe
página para ele) e contado em `etl_runs`, para não parecer perda silenciosa.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.sources import cvm
from alpherion.db.models import FiiReport, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "cvm_fii_reports"
SOURCE = "cvm"


def run(*, year: int | None = None) -> None:
    target = year or date.today().year
    with base.run(JOB, period=date(target, 1, 1), source=SOURCE) as ctx:
        by_cnpj = _fii_tickers(ctx)
        reports = cvm.fetch_fii_monthly(target)

        rows = []
        sem_ticker = 0
        for report in reports:
            ticker = by_cnpj.get(report.cnpj)
            if ticker is None:
                sem_ticker += 1
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "period": report.period,
                    "nav": report.nav,
                    "nav_per_share": report.nav_per_share,
                    "shares": report.shares,
                    "shareholders": report.shareholders,
                    "income_per_share": report.income_per_share,
                    "vacancy_physical": report.vacancy_physical,
                    "vacancy_financial": report.vacancy_financial,
                    "admin_fee": report.admin_fee,
                    "manager": report.manager,
                    "administrator": report.administrator,
                    "segment": report.segment,
                }
            )

        ctx.wrote(upsert(ctx.session, FiiReport, rows))
        ctx.notes["informes_sem_papel_listado"] = sem_ticker


def _fii_tickers(ctx: base.JobContext) -> dict[str, str]:
    rows = ctx.session.execute(
        select(Security.cnpj, Security.ticker).where(
            Security.type.in_(("fii", "fiagro")), Security.cnpj.is_not(None)
        )
    )
    return {cnpj: ticker for cnpj, ticker in rows if cnpj}


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
