"""Partições anuais de `market.daily_quotes`.

O Postgres não cria partição sozinho: sem a partição do ano, o INSERT falha. Quem
chama isto é a migration (histórico) e o job `cotahist_daily` no primeiro pregão do ano.

A função é idempotente (`IF NOT EXISTS`) e serve tanto para criar o passado quanto
para preparar o próximo ano.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.engine import Connection

#: COTAHIST começa em 1986; o backfill completo cria daí para frente.
FIRST_YEAR = 1986


def partition_name(table: str, year: int) -> str:
    return f"{table}_{year}"


def create_year_partition(
    connection: Connection, year: int, *, table: str = "daily_quotes"
) -> None:
    """Cria a partição de um ano, se ainda não existir."""
    name = partition_name(table, year)
    connection.execute(
        text(
            f'CREATE TABLE IF NOT EXISTS market."{name}" '
            f'PARTITION OF market."{table}" '
            f"FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01')"
        )
    )


def create_year_partitions(
    connection: Connection, years: Iterable[int], *, table: str = "daily_quotes"
) -> None:
    for year in years:
        create_year_partition(connection, year, table=table)
