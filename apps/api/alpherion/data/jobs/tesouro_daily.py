"""Preços e taxas do Tesouro Direto (diário).

Fonte liberada (ODbL): `/tesouro` é a única página de preço que sai no ar sem a licença
da B3 (ADR-017).

O CSV do Tesouro Transparente traz a série inteira em um arquivo só, então o job carrega
os últimos dias e deixa o histórico completo para o `backfill-market.sh`. O título em si
(`treasury_bonds`) é upsertado junto: vencimento novo aparece no CSV antes de qualquer
outro lugar.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from alpherion.data.jobs import base
from alpherion.data.sources import tesouro
from alpherion.db.models import TreasuryBond, TreasuryDaily
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "tesouro_daily"
SOURCE = "tesouro"
#: Janela do job diário. O Tesouro corrige preço retroativo; reler alguns dias é barato.
DEFAULT_WINDOW_DAYS = 10


def run(*, since: date | None = None, full: bool = False) -> None:
    start = None if full else (since or date.today() - timedelta(days=DEFAULT_WINDOW_DAYS))
    with base.run(JOB, period=date.today(), source=SOURCE) as ctx:
        bonds: dict[str, dict[str, object]] = {}
        quotes: list[dict[str, object]] = []

        for row in tesouro.fetch():
            if start is not None and row.date < start:
                continue
            bonds.setdefault(
                row.slug,
                {
                    "slug": row.slug,
                    "name": row.name,
                    "index_type": row.index_type,
                    "maturity": row.maturity,
                    "coupon": row.coupon,
                },
            )
            quotes.append(
                {
                    "slug": row.slug,
                    "date": row.date,
                    "buy_rate": row.buy_rate,
                    "sell_rate": row.sell_rate,
                    "buy_price": row.buy_price,
                    "sell_price": row.sell_price,
                }
            )

        ctx.wrote(upsert(ctx.session, TreasuryBond, list(bonds.values())))
        ctx.wrote(upsert(ctx.session, TreasuryDaily, quotes))
        ctx.notes["titulos"] = len(bonds)


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
