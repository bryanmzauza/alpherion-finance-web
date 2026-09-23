"""Cadastro dos papéis listados: ações, units, ETFs, BDRs, FIIs e fiagros.

É o job que faz existir `/acoes/PETR4`, `/fiis/MXRF11`, `/etfs/BOVA11` e `/bdrs/AAPL34`.
As fontes e como se casam estão em `sources/b3_listing.py`.

**Nada é apagado.** Papel que sai da listagem vira `inactive` (a página continua no ar,
com o cadastro e o histórico que já existiam); `DELETE` aqui derrubaria página indexada
por causa de uma resposta ruim da B3. E a inativação só acontece quando o arquivo do dia
tem volume plausível (`MIN_LISTED`): um arquivo truncado não pode "deslistar" a bolsa.

Classificação setorial e emissores são complementares: se um deles falha, os papéis
entram assim mesmo, sem setor ou sem CNPJ, e a falta fica em `etl_runs`. O que não pode
faltar é o cadastro de instrumentos — sem ele o job falha e o cadastro atual continua.

`sectors` é remontada a partir do que ficou em `securities` (`rebuild_sectors`), que o
`cvm_fii_reports` também chama depois de gravar o segmento dos FIIs.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from alpherion.data.jobs import base
from alpherion.data.sources import b3_listing as source
from alpherion.data.sources.b3_api import B3UnavailableError
from alpherion.data.sources.http import SourceError
from alpherion.db.models import Sector, Security
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "b3_listing"
SOURCE = "b3"

#: Abaixo disto o arquivo do dia é suspeito (a B3 tem ~2,5 mil papéis à vista entre
#: ações, BDRs e fundos): grava o que veio, mas não inativa ninguém.
MIN_LISTED = 800

#: Colunas que esta carga sobrescreve em todo papel. `cnpj` e `cvm_code` ficam de fora
#: quando vierem vazios: `cvm_companies` também os preenche.
UPDATE_COLUMNS = ("type", "company_name", "trade_name", "isin", "listing_segment", "status")

#: Setor só é sobrescrito em papel com classificação B3. Em FII quem grava o segmento é
#: o `cvm_fii_reports`, e a carga das 7h não pode apagá-lo todo dia.
SECTOR_COLUMNS = ("sector", "subsector", "segment", "sector_slug")


def run() -> None:
    today = date.today()
    with base.run(JOB, period=today, source=SOURCE) as ctx:
        day, instruments = source.fetch_instruments(today)
        ctx.notes["arquivo_de_instrumentos"] = day.isoformat()

        try:
            classification = source.fetch_classification()
        except (B3UnavailableError, SourceError) as error:
            logger.warning(
                "classificação setorial indisponível: %s — papéis entram sem setor", error
            )
            ctx.notes["classificacao_setorial"] = "indisponível"
            classification = {}
        try:
            issuers = source.fetch_issuers()
        except (B3UnavailableError, SourceError) as error:
            logger.warning("emissores indisponíveis: %s — papéis entram sem CNPJ/código CVM", error)
            ctx.notes["emissores"] = "indisponível"
            issuers = {}

        listed = list(source.build_listing(instruments, classification, issuers))
        ctx.notes["papeis_por_tipo"] = _count_by_type(listed)
        ctx.wrote(save(ctx.session, listed, has_classification=bool(classification)))

        if len(listed) >= MIN_LISTED:
            ctx.notes["inativados"] = deactivate_missing(ctx.session, {s.ticker for s in listed})
        else:
            logger.warning("só %d papéis no arquivo — ninguém é inativado hoje", len(listed))
            ctx.notes["inativados"] = "não aplicado (arquivo pequeno demais)"

        ctx.wrote(rebuild_sectors(ctx.session))


def _count_by_type(listed: list[source.ListedSecurity]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in listed:
        counts[item.type] = counts.get(item.type, 0) + 1
    return counts


def _row(item: source.ListedSecurity) -> dict[str, object]:
    return {
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


def save(session: Session, listed: list[source.ListedSecurity], *, has_classification: bool) -> int:
    """Grava em dois lotes: quem tem setor da B3 e quem não tem (fundos, ou dia sem planilha)."""
    classified = [_row(i) for i in listed if not i.is_fund and has_classification]
    others = [_row(i) for i in listed if i.is_fund or not has_classification]
    written = upsert(session, Security, classified, update=[*UPDATE_COLUMNS, *SECTOR_COLUMNS])
    written += upsert(session, Security, others, update=list(UPDATE_COLUMNS))
    # CNPJ e código CVM: preenche quando vieram, nunca apaga o que o `cvm_companies` pôs.
    for item in listed:
        if item.cnpj or item.cvm_code:
            values = {k: v for k, v in (("cnpj", item.cnpj), ("cvm_code", item.cvm_code)) if v}
            session.execute(update(Security).where(Security.ticker == item.ticker).values(**values))
    return written


def deactivate_missing(session: Session, tickers: set[str]) -> int:
    """Quem não está no arquivo do dia vira `inactive`. Nunca `DELETE`."""
    result = session.execute(
        update(Security)
        .where(
            Security.status == "active", Security.market == "br", Security.ticker.not_in(tickers)
        )
        .values(status="inactive")
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def rebuild_sectors(session: Session) -> int:
    """Remonta `sectors` a partir de `securities`, com a contagem factual de papéis ativos.

    FII e fiagro viram `fii_segment`; o resto, `b3_segment`. Segmento que ficou sem
    nenhum papel ativo sai da tabela — ela é derivada, e um setor vazio seria página
    sem conteúdo.
    """
    rows = session.execute(
        select(
            Security.sector_slug,
            func.max(Security.segment),
            func.max(Security.sector),
            func.max(Security.subsector),
            func.bool_or(Security.type.in_(("fii", "fiagro"))),
            func.count(),
        )
        .where(Security.sector_slug.is_not(None), Security.status == "active")
        .group_by(Security.sector_slug)
    ).all()
    nodes = [
        {
            "slug": slug,
            "name": segment or subsector or sector or slug,
            "kind": "fii_segment" if is_fund else "b3_segment",
            "sector": sector,
            "subsector": subsector,
            "securities_count": count,
        }
        for slug, segment, sector, subsector, is_fund, count in rows
        if slug
    ]
    session.execute(delete(Sector).where(Sector.slug.not_in([n["slug"] for n in nodes] or [""])))
    return upsert(session, Sector, nodes)


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
