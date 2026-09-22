"""Cadastro de companhias abertas e de FIIs (CVM).

Fonte liberada. É a carga que dá ao `securities` razão social, CNPJ e código CVM — o elo
entre o ticker (que vem da B3) e as demonstrações (que vêm da CVM).

**Só preenche o que a CVM sabe.** O cadastro da CVM não tem ticker, e o job nunca
inventa um: quando não há `securities` correspondente (por CNPJ ou `cvm_code`), a
companhia fica registrada e a página existe quando a listagem da B3 trouxer o papel.
Papel algum é apagado aqui — cadastro que some da fonte vira `inactive`, não sumiço.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select, update

from alpherion.data.jobs import base
from alpherion.data.sources import cvm
from alpherion.db.models import Security

logger = logging.getLogger(__name__)

JOB = "cvm_companies"
SOURCE = "cvm"


def run() -> None:
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        by_cvm_code = {c.cvm_code: c for c in cvm.fetch_companies()}
        by_cnpj = {c.cnpj: c for c in by_cvm_code.values() if c.cnpj}
        logger.info("CVM: %d companhias no cadastro", len(by_cvm_code))

        atualizados = 0
        for ticker, cvm_code, cnpj in ctx.session.execute(
            select(Security.ticker, Security.cvm_code, Security.cnpj)
        ):
            company = by_cvm_code.get(cvm_code) or (by_cnpj.get(cnpj) if cnpj else None)
            if company is None:
                continue
            ctx.session.execute(
                update(Security)
                .where(Security.ticker == ticker)
                .values(
                    cvm_code=company.cvm_code,
                    cnpj=company.cnpj or cnpj,
                    company_name=company.company_name,
                    trade_name=company.trade_name,
                    ri_url=company.ri_url,
                    status=company.status,
                )
            )
            atualizados += 1

        ctx.wrote(atualizados)
        ctx.notes["companhias_na_fonte"] = len(by_cvm_code)
        ctx.notes["sem_papel_listado"] = len(by_cvm_code) - atualizados


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
