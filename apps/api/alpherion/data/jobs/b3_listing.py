"""Cadastro dos papéis listados: ações, units, ETFs, BDRs e FIIs.

É o job que faz existir `/acoes/PETR4`, `/fiis/MXRF11`, `/etfs/BOVA11` e `/bdrs/AAPL34`.
Depois dele, `cvm_companies` completa razão social e código CVM.

**Nada é apagado.** Papel que sai da listagem vira `inactive` (a página continua no ar,
com o cadastro e o histórico que já existiam); `DELETE` aqui derrubaria página indexada
por causa de uma resposta ruim da B3. E, se um bloco falha, os outros seguem: uma queda
do endpoint de ETFs não pode deixar o cadastro de ações sem atualizar.

`sectors` é remontada a partir do que ficou em `securities`: `/setores` é página
indexável e precisa de nome estável e contagem factual.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from functools import partial

from sqlalchemy import func, select

from alpherion.data.jobs import base
from alpherion.data.sources import b3_listing as source
from alpherion.data.sources.b3_api import B3UnavailableError
from alpherion.db.models import Sector, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "b3_listing"
SOURCE = "b3"

#: Colunas que esta carga sobrescreve. `cvm_code`, `cnpj` e `ri_url` ficam de fora
#: quando vierem vazios: quem os preenche é o `cvm_companies`.
UPDATE_COLUMNS = (
    "type",
    "company_name",
    "trade_name",
    "sector",
    "subsector",
    "segment",
    "sector_slug",
    "listing_segment",
    "etf_index_slug",
    "bdr_ratio",
    "status",
)


def run() -> None:
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        blocos: tuple[tuple[str, Callable[[], list[source.ListedSecurity]]], ...] = (
            ("companhias", source.fetch_companies),
            ("fiis", partial(source.fetch_funds, "fii")),
            ("etfs", partial(source.fetch_funds, "etf")),
            ("fiagros", partial(source.fetch_funds, "fiagro")),
            ("bdrs", source.fetch_bdrs),
        )
        falhas: list[str] = []
        for label, fetch in blocos:
            try:
                listed = fetch()
            except B3UnavailableError as error:
                falhas.append(label)
                logger.warning("B3 %s indisponível: %s — cadastro atual mantido", label, error)
                continue
            ctx.wrote(_save(ctx, listed))

        if falhas:
            ctx.notes["blocos_com_falha"] = falhas
        _rebuild_sectors(ctx)


def _save(ctx: base.JobContext, listed: list[source.ListedSecurity]) -> int:
    rows = [
        {
            "ticker": item.ticker,
            "type": item.type,
            "company_name": item.company_name,
            "trade_name": item.trade_name,
            "cnpj": item.cnpj,
            "cvm_code": item.cvm_code,
            "isin": item.isin,
            "sector": item.sector,
            "subsector": item.subsector,
            "segment": item.segment,
            "sector_slug": item.sector_slug,
            "listing_segment": item.listing_segment,
            "etf_index_slug": item.etf_index_slug,
            "bdr_ratio": item.bdr_ratio,
            "status": "active",
        }
        for item in listed
        # Papel que não dá para classificar não entra: melhor faltar do que aparecer
        # na classe errada (uma ação na lista de FIIs).
        if item.type != "other"
    ]
    return upsert(ctx.session, Security, rows, update=list(UPDATE_COLUMNS))


def _rebuild_sectors(ctx: base.JobContext) -> None:
    """Remonta `sectors` com a contagem factual de papéis ativos por segmento."""
    rows = ctx.session.execute(
        select(
            Security.sector_slug,
            func.max(Security.segment),
            func.max(Security.sector),
            func.max(Security.subsector),
            func.count(),
        )
        .where(Security.sector_slug.is_not(None), Security.status == "active")
        .group_by(Security.sector_slug)
    )
    ctx.wrote(
        upsert(
            ctx.session,
            Sector,
            [
                {
                    "slug": slug,
                    "name": segment or subsector or sector or slug,
                    "kind": "b3_segment",
                    "sector": sector,
                    "subsector": subsector,
                    "securities_count": count,
                }
                for slug, segment, sector, subsector, count in rows
                if slug
            ],
        )
    )


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
