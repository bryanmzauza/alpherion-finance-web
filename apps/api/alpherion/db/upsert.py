"""`INSERT ... ON CONFLICT DO UPDATE` — o que torna os jobs idempotentes.

Um job do pipeline sempre pode rodar de novo: a fonte republica, o worker cai no meio,
o runbook manda reprocessar o dia. Se a segunda execução duplicasse linha ou apagasse
dado, "reprocessar" viraria uma operação de risco — e reprocessar é rotina aqui.

A regra é a mesma em todas as tabelas: chave natural (ticker + data, cvm_code + período,
protocolo) decide o conflito, e a carga nova sobrescreve as colunas que trouxe.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from alpherion.db.base import Base

logger = logging.getLogger(__name__)

#: Lotes grandes demais estouram o limite de parâmetros do Postgres (65535).
CHUNK_SIZE = 500


def upsert(
    session: Session,
    model: type[Base],
    rows: Sequence[dict[str, Any]],
    *,
    conflict: Sequence[str] | None = None,
    update: Sequence[str] | None = None,
) -> int:
    """Insere ou atualiza `rows`, devolvendo quantas linhas foram enviadas.

    `conflict` é a chave natural (por padrão, a primária). `update` limita as colunas
    sobrescritas — é o que permite a uma carga parcial (só preço, só cadastro) não
    apagar o que outra carga preencheu.
    """
    if not rows:
        return 0
    table: Table = model.__table__  # type: ignore[assignment]
    keys = list(conflict) if conflict else [column.name for column in table.primary_key]
    updatable = list(update) if update else [c for c in rows[0] if c not in keys]

    total = 0
    for batch in _chunks(rows, CHUNK_SIZE):
        statement = insert(table).values(batch)
        if updatable:
            statement = statement.on_conflict_do_update(
                index_elements=keys,
                set_={name: getattr(statement.excluded, name) for name in updatable},
            )
        else:
            statement = statement.on_conflict_do_nothing(index_elements=keys)
        session.execute(statement)
        total += len(batch)
    logger.debug("%s: %d linhas gravadas", table.name, total)
    return total


def _chunks(rows: Sequence[dict[str, Any]], size: int) -> Iterable[Sequence[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]
