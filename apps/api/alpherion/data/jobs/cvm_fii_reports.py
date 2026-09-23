"""Informes mensais dos fundos imobiliários (CVM).

Fonte liberada. Dá a `/fiis/[ticker]` patrimônio, valor patrimonial da cota, número de
cotistas, taxa de administração e — quando o fundo informa — vacância. O P/VP do FII sai
daqui (`nav_per_share`), não do balanço.

O informe é por **CNPJ**; `fii_reports` é por ticker. A conversão é feita aqui pelo
**ISIN** da cota, que o informe e o cadastro de instrumentos da B3 trazem (o cadastro da
B3 não traz o CNPJ do fundo); o CNPJ fica como reserva. Informe de fundo que não está
listado é ignorado (não existe página para ele) e contado em `etl_runs`, para não
parecer perda silenciosa.

O **segmento** informado (Logística, Shoppings, Títulos e Val. Mob.…) é o que alimenta os
segmentos de FII em `/setores`: o do informe mais recente vai para `securities`, e a
árvore é remontada.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select, update

from alpherion.data.jobs import base
from alpherion.data.jobs.b3_listing import rebuild_sectors
from alpherion.data.sources import cvm
from alpherion.data.sources.b3_listing import slugify
from alpherion.db.models import FiiReport, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "cvm_fii_reports"
SOURCE = "cvm"


def run(*, year: int | None = None) -> None:
    target = year or date.today().year
    with base.run(JOB, period=date(target, 1, 1), source=SOURCE) as ctx:
        by_isin, by_cnpj = _fii_tickers(ctx)
        reports = cvm.fetch_fii_monthly(target)

        by_key: dict[tuple[str, date], list[cvm.FiiReportRow]] = {}
        sem_ticker = 0
        for report in reports:
            ticker = (by_isin.get(report.isin) if report.isin else None) or by_cnpj.get(report.cnpj)
            if ticker is None:
                sem_ticker += 1
                continue
            by_key.setdefault((ticker, report.period), []).append(report)

        rows = []
        ambiguos = 0
        latest_segment: dict[str, tuple[date, str]] = {}
        for (ticker, period), candidates in by_key.items():
            chosen = pick_report(candidates)
            if chosen is None:
                ambiguos += 1
                continue
            report = chosen
            rows.append(
                {
                    "ticker": ticker,
                    "period": period,
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
            if report.segment and period >= latest_segment.get(ticker, (date.min, ""))[0]:
                latest_segment[ticker] = (period, report.segment)

        ctx.wrote(upsert(ctx.session, FiiReport, rows))
        ctx.notes["informes_sem_papel_listado"] = sem_ticker
        ctx.notes["meses_com_isin_ambiguo"] = ambiguos

        for ticker, (_period, segment) in latest_segment.items():
            ctx.session.execute(
                update(Security)
                .where(Security.ticker == ticker)
                .values(segment=segment, sector_slug=fii_segment_slug(segment))
            )
        ctx.notes["fiis_com_segmento"] = len(latest_segment)
        ctx.wrote(rebuild_sectors(ctx.session))


def pick_report(candidates: list[cvm.FiiReportRow]) -> cvm.FiiReportRow | None:
    """O informe de um ticker num mês, quando mais de um fundo diz ser o dono do ISIN.

    Fica o único que negocia em bolsa. Se ainda houver empate, nenhum: escolher no chute
    poria o patrimônio de um fundo na página de outro.
    """
    if len({c.cnpj for c in candidates}) == 1:
        return max(candidates, key=lambda c: c.version)
    listed = [c for c in candidates if c.exchange_listed]
    if len({c.cnpj for c in listed}) == 1:
        return max(listed, key=lambda c: c.version)
    return None


def fii_segment_slug(segment: str) -> str | None:
    """`Logística` → `fii-logistica`: o prefixo separa do segmento B3 de mesmo nome."""
    return slugify("fii", segment)


def _fii_tickers(ctx: base.JobContext) -> tuple[dict[str, str], dict[str, str]]:
    """(ISIN → ticker, CNPJ → ticker) dos fundos listados."""
    rows = ctx.session.execute(
        select(Security.isin, Security.cnpj, Security.ticker).where(
            Security.type.in_(("fii", "fiagro"))
        )
    ).all()
    by_isin = {isin: ticker for isin, _cnpj, ticker in rows if isin}
    by_cnpj = {cnpj: ticker for _isin, cnpj, ticker in rows if cnpj}
    return by_isin, by_cnpj


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
