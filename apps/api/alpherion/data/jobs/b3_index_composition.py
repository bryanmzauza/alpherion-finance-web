"""Carteira teórica dos índices da B3.

Alimenta `/indices/[slug]` (a tabela de composição, sempre com a data ao lado), o
`etf_index_slug` dos ETFs e a faixa do header.

**A carteira anterior nunca é apagada.** A composição é guardada por data
(`index_compositions.date`), então o histórico fica e a página mostra a vigente com a
data — "carteira de 02/09/2026", não "composição do Ibovespa". Quando o endpoint falha,
a última carteira continua valendo e a data à vista diz ao leitor o quanto ela é antiga
(§3.2 do plano): melhor uma carteira datada de ontem do que uma tabela vazia hoje.
"""

from __future__ import annotations

import logging
from datetime import date

from alpherion.data.jobs import base
from alpherion.data.sources import b3_indices
from alpherion.data.sources.b3_api import B3UnavailableError
from alpherion.db.models import IndexComposition, MarketIndex
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "b3_index_composition"
SOURCE = "b3"


def run(*, slugs: list[str] | None = None) -> None:
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
            except B3UnavailableError as error:
                falhas.append(slug)
                logger.warning("carteira de %s indisponível: %s — mantida a última", slug, error)
                continue
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
        if falhas:
            ctx.notes["indices_com_falha"] = falhas


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
