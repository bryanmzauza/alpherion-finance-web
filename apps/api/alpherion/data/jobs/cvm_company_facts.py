"""Capital social das companhias (FRE da CVM): quantas ações existem.

Fonte liberada. É o número que transforma lucro em LPA, patrimônio em VPA e preço em
valor de mercado — sem ele, P/L, P/VP e market cap ficam "—" com o motivo
("quantidade de ações não disponível"), como ficaram até este job existir.

O FRE identifica a companhia pelo CNPJ; `company_facts` é por código CVM. A conversão
usa o cadastro de `securities` (que recebe CNPJ e código CVM da B3 e da CVM). Companhia
sem papel listado é contada e ignorada.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.sources import cvm
from alpherion.data.sources.http import SourceError
from alpherion.db.models import CompanyFact, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "cvm_company_facts"
SOURCE = "cvm"


def run(*, year: int | None = None) -> None:
    """Carrega o FRE de um ano. Sem `year`, o do ano corrente e, se faltar, o anterior."""
    target = year or date.today().year
    with base.run(JOB, period=date(target, 1, 1), source=SOURCE) as ctx:
        try:
            facts = cvm.fetch_company_facts(target)
        except SourceError:
            if year is not None:
                raise
            # No começo do ano o FRE novo ainda não saiu: o do ano anterior vale.
            logger.info("FRE %d indisponível; usando o de %d", target, target - 1)
            facts = cvm.fetch_company_facts(target - 1)

        by_cnpj = _cvm_codes(ctx)
        rows: dict[tuple[int, date], dict[str, object]] = {}
        sem_papel = 0
        for fact in facts:
            code = fact.cvm_code or (by_cnpj.get(fact.cnpj) if fact.cnpj else None)
            if code is None:
                sem_papel += 1
                continue
            # Uma linha por (código CVM, data): o upsert não aceita a chave duas vezes.
            rows[(code, fact.reference_date)] = {
                "cvm_code": code,
                "reference_date": fact.reference_date,
                "shares_outstanding": fact.shares_outstanding,
                "capital_social": fact.capital_social,
            }
        ctx.wrote(upsert(ctx.session, CompanyFact, list(rows.values())))
        ctx.notes["companhias_sem_papel_listado"] = sem_papel


def _cvm_codes(ctx: base.JobContext) -> dict[str, int]:
    rows = ctx.session.execute(
        select(Security.cnpj, Security.cvm_code).where(
            Security.cnpj.is_not(None), Security.cvm_code.is_not(None)
        )
    )
    return {cnpj: code for cnpj, code in rows if cnpj and code}


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
