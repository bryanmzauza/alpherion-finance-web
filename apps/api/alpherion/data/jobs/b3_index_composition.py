"""Carteira teórica e fechamento diário dos índices da B3.

Alimenta `/indices/[slug]` (a tabela de composição, sempre com a data ao lado, e o
histórico), o `etf_index_slug` dos ETFs, a faixa do header e a Leitura de Mercado.

O fechamento (`index_daily`) vem da grade anual de "Estatísticas históricas" da B3; a
variação do dia é calculada sobre o fechamento anterior, inclusive na virada do ano
(o de 30/12 vem do banco ou da grade do ano anterior).

**A carteira anterior nunca é apagada.** A composição é guardada por data
(`index_compositions.date`), então o histórico fica e a página mostra a vigente com a
data — "carteira de 02/09/2026", não "composição do Ibovespa". Quando o endpoint falha,
a última carteira continua valendo e a data à vista diz ao leitor o quanto ela é antiga
(§3.2 do plano): melhor uma carteira datada de ontem do que uma tabela vazia hoje.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.sources import b3_indices
from alpherion.data.sources.b3_api import B3UnavailableError
from alpherion.data.sources.http import SourceError
from alpherion.db.models import IndexComposition, IndexDaily, MarketIndex
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "b3_index_composition"
SOURCE = "b3"


def run(*, slugs: list[str] | None = None, years: int = 1) -> None:
    """`years` > 1 é o backfill: relê a grade de fechamentos dos últimos N anos."""
    alvos = slugs or list(b3_indices.INDICES)
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        # O índice em si é cadastro estável: registrá-lo antes garante que a página
        # exista mesmo se a carteira do dia não vier.
        ctx.wrote(
            upsert(
                ctx.session,
                MarketIndex,
                [
                    {"slug": slug, "b3_code": code, "name": _display_name(slug)}
                    for slug, code in b3_indices.INDICES.items()
                    if slug in alvos
                ],
                update=["b3_code"],
            )
        )

        falhas: list[str] = []
        for slug in alvos:
            try:
                members = b3_indices.fetch_composition(slug)
            except (B3UnavailableError, SourceError) as error:
                falhas.append(slug)
                logger.warning("carteira de %s indisponível: %s — mantida a última", slug, error)
                members = []  # a última carteira gravada continua valendo
            ctx.wrote(
                upsert(
                    ctx.session,
                    IndexComposition,
                    [
                        {
                            "slug": member.index_slug,
                            "date": member.reference_date,
                            "ticker": member.ticker,
                            "weight": member.weight,
                            "theoretical_qty": member.theoretical_quantity,
                        }
                        for member in members
                    ],
                )
            )

            try:
                ctx.wrote(_save_closes(ctx, slug, years=years))
            except (B3UnavailableError, SourceError) as error:
                falhas.append(f"{slug} (fechamentos)")
                logger.warning("fechamentos de %s indisponíveis: %s", slug, error)
        if falhas:
            ctx.notes["indices_com_falha"] = falhas


def _save_closes(ctx: base.JobContext, slug: str, *, years: int) -> int:
    """Grava os fechamentos dos últimos `years` anos, com a variação de cada dia."""
    this_year = date.today().year
    closes: list[b3_indices.IndexClose] = []
    for year in range(this_year - max(1, years) + 1, this_year + 1):
        closes.extend(b3_indices.fetch_year_closes(slug, year))
    if not closes:
        return 0
    first = min(c.date for c in closes)
    stored = ctx.session.execute(
        select(IndexDaily.value)
        .where(IndexDaily.slug == slug, IndexDaily.date < first)
        .order_by(IndexDaily.date.desc())
        .limit(1)
    ).scalar()
    previous = Decimal(str(stored)) if stored is not None else None
    if previous is None and first.month == 1:
        # Primeiro pregão do ano sem histórico no banco: o anterior está na grade de lá.
        before = b3_indices.fetch_year_closes(slug, first.year - 1)
        previous = before[-1].close if before else None
    return upsert(
        ctx.session,
        IndexDaily,
        [
            {"slug": c.index_slug, "date": c.date, "value": c.close, "change_pct": c.change_percent}
            for c in b3_indices.with_changes(closes, previous)
        ],
    )


def _display_name(slug: str) -> str:
    """Nome de exibição do índice. O slug é a URL; o nome é o que aparece na página."""
    especiais = {
        "ibovespa": "Ibovespa",
        "ifix": "IFIX",
        "idiv": "IDIV",
        "smll": "SMLL",
        "ibrx-100": "IBrX 100",
        "ibra": "IBrA",
        "ifnc": "IFNC",
        "imob": "IMOB",
        "util": "UTIL",
    }
    return especiais.get(slug, slug.upper())


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
