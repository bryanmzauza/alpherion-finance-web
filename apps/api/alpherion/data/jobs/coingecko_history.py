"""Histórico diário de criptoativos (uma vez por dia).

Mesma trava do `coingecko_prices` (ADR-017): em produção fica `skipped` até haver fonte
licenciada.

O CoinGecko limita requisições com folga curta no plano gratuito, e este job faz uma
chamada por ativo. Por isso ele **pausa entre os ativos** e para no primeiro 429 em vez
de insistir: o que já carregou fica gravado, e a próxima execução continua de onde
parou — o upsert por (ativo, dia) torna isso gratuito.
"""

from __future__ import annotations

import logging
import time
from datetime import date

from sqlalchemy import select

from alpherion.data.jobs import base
from alpherion.data.sources import coingecko
from alpherion.data.sources.http import SourceError
from alpherion.db.models import CryptoAsset, CryptoDaily
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "coingecko_history"
SOURCE = "coingecko"
#: Janela do job diário; o backfill pede a série longa.
DEFAULT_DAYS = 90
#: Pausa entre ativos, para não bater no limite de requisições.
SLEEP_SECONDS = 1.5


def run(*, days: int = DEFAULT_DAYS, asset_ids: list[str] | None = None) -> None:
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        alvos = asset_ids or _tracked_assets(ctx)
        for position, asset_id in enumerate(alvos):
            try:
                points = coingecko.fetch_history(asset_id, days=days)
            except SourceError as error:
                # Parar e gravar o que veio é melhor que insistir e ser bloqueado: a
                # próxima execução continua daqui.
                ctx.notes["parou_em"] = asset_id
                logger.warning("histórico de %s: %s — parando por aqui", asset_id, error)
                break
            ctx.wrote(
                upsert(
                    ctx.session,
                    CryptoDaily,
                    [
                        {
                            "id": point.asset_id,
                            "date": point.date,
                            "price_brl": point.price,
                            "market_cap_brl": point.market_cap,
                            "volume_brl": point.volume,
                        }
                        for point in points
                    ],
                    update=["price_brl", "market_cap_brl", "volume_brl"],
                )
            )
            if position < len(alvos) - 1:
                time.sleep(SLEEP_SECONDS)


def _tracked_assets(ctx: base.JobContext) -> list[str]:
    rows = ctx.session.execute(
        select(CryptoAsset.id).order_by(CryptoAsset.market_cap_rank.nulls_last())
    )
    return [asset_id for (asset_id,) in rows]


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
