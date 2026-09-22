"""Cotações do pregão (COTAHIST da B3).

ADR-017: roda em dev e no pipeline; o que sai para o público depende de
`MARKET_B3_PRICES_ENABLED` e da licença. Em produção, `data_sources` sem
`terms_checked_at` faz o job terminar como `skipped` — a base dessa checagem é
`jobs/base.py`.

Duas coisas que só este job precisa saber:

- **A partição do ano tem de existir antes do INSERT.** O Postgres não cria sozinho, e
  no primeiro pregão de janeiro o job quebraria se não criasse (`db/partitions.py`).
- **O arquivo do dia só existe em dia de pregão.** Feriado e fim de semana devolvem 404,
  que aqui é `skipped` e não `failed`: não há incidente nenhum em não haver pregão.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta

from alpherion.data.jobs import base
from alpherion.data.sources import b3_cotahist
from alpherion.data.sources.http import SourceError
from alpherion.db.models import DailyQuote
from alpherion.db.partitions import create_year_partition
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "cotahist_daily"
SOURCE = "b3"


def run(*, day: date | None = None) -> None:
    """Carrega um pregão. Sem `day`, o do dia corrente."""
    target = day or date.today()
    with base.run(JOB, period=target, source=SOURCE) as ctx:
        create_year_partition(ctx.session.connection(), target.year)

        try:
            quotes = list(b3_cotahist.fetch_day(target))
        except SourceError as error:
            # 404 em feriado e fim de semana é o caso normal, não uma falha do pipeline.
            raise base.JobSkipped(f"sem arquivo para {target:%d/%m/%Y}: {error}") from error

        ctx.wrote(
            upsert(
                ctx.session,
                DailyQuote,
                [
                    {
                        "ticker": quote.ticker,
                        "date": quote.date,
                        "open": quote.open,
                        "high": quote.high,
                        "low": quote.low,
                        "close": quote.close,
                        "volume": quote.volume,
                        "quantity": quote.quantity,
                        "trades": quote.trades,
                    }
                    for quote in quotes
                ],
                # `close_adjusted` e `adj_factor` são do `adjust_factors`: uma carga de
                # preço bruto não pode apagar o ajuste já calculado.
                update=["open", "high", "low", "close", "volume", "quantity", "trades"],
            )
        )


def run_year(*, year: int, only: list[str] | None = None) -> None:
    """Carrega um ano inteiro (backfill). `only` limita aos papéis de interesse.

    O arquivo anual passa de 200 MB descomprimido e traz todo papel que já existiu;
    em desenvolvimento, filtrar por uma amostra é a diferença entre um banco de
    centenas de MB e um de poucos.
    """
    wanted = {ticker.upper() for ticker in only} if only else None
    with base.run(JOB, period=date(year, 1, 1), source=SOURCE) as ctx:
        create_year_partition(ctx.session.connection(), year)
        rows = [
            {
                "ticker": quote.ticker,
                "date": quote.date,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "close": quote.close,
                "volume": quote.volume,
                "quantity": quote.quantity,
                "trades": quote.trades,
            }
            for quote in b3_cotahist.fetch_year(year)
            if wanted is None or quote.ticker in wanted
        ]
        ctx.wrote(
            upsert(
                ctx.session,
                DailyQuote,
                rows,
                update=["open", "high", "low", "close", "volume", "quantity", "trades"],
            )
        )


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Carrega as cotações de um pregão.")
    parser.add_argument("--data", default=None, help="pregão em aaaa-mm-dd (padrão: hoje)")
    parser.add_argument("--dias", type=int, default=1, help="quantos pregões para trás")
    parser.add_argument("--ano", type=int, default=None, help="ano inteiro (backfill)")
    args = parser.parse_args()

    if args.ano:
        run_year(year=args.ano)
        return

    start = datetime.strptime(args.data, "%Y-%m-%d").date() if args.data else date.today()
    for offset in range(args.dias):
        run(day=start - timedelta(days=offset))


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(_cli)
