"""Esqueleto de todo job do pipeline (site.md §3.5, plano §3.3).

Um job do worker `data` é sempre a mesma coisa: pega um lock, registra o início em
`etl_runs`, lê de uma fonte, grava em `market` com upsert e registra o fim. O que muda
é o miolo. Tudo o mais está aqui, uma vez só, porque são justamente essas bordas que
decidem se o pipeline é operável:

- **Lock no Redis.** Dois workers, ou um cron que dispara enquanto o anterior ainda
  roda, não podem carregar o mesmo período duas vezes. O lock tem TTL (o processo pode
  morrer) e só é solto por quem o pegou — comparação do token antes do `DEL`.
- **`etl_runs` sempre fechado.** Sucesso, falha ou pulo: a linha é fechada no `finally`.
  É dela que sai o alerta de frescor ("`cotahist_daily` não rodou até 21h", §3.6).
- **Licença bloqueia em produção (ADR-017).** Fonte sem `terms_checked_at` em
  `data_sources` não roda em produção — o job termina como `skipped`, com o motivo, e
  não como sucesso vazio. Em dev roda normalmente: processar não é distribuir.
- **Falha não derruba o worker.** A exceção é registrada em `etl_runs.error` e
  re-levantada para o cron enxergar o código de saída; nenhum job engole erro em
  silêncio, porque tabela vazia por erro silencioso é o pior estado possível.

Cada job é um módulo executável: `python -m alpherion.data.jobs.<job>`.
"""

from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Any

import redis
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from alpherion.db.models import DataSource, EtlRun
from alpherion.settings import get_settings

logger = logging.getLogger(__name__)

#: TTL do lock: mais longo que o job mais demorado (backfill de um ano de COTAHIST),
#: curto o bastante para um worker morto não travar o pipeline até o dia seguinte.
LOCK_TTL_SECONDS = 4 * 60 * 60
LOCK_PREFIX = "alpherion:job:"

#: Solta o lock **só se ainda for nosso**: entre o TTL expirar e o `DEL`, outro worker
#: pode já ter pegado o mesmo lock, e apagá-lo liberaria dois jobs ao mesmo tempo.
_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class JobSkipped(Exception):  # noqa: N818 - não é erro: o job decidiu não rodar
    """O job não tinha o que fazer (lock ocupado, fonte bloqueada, período já carregado)."""


@lru_cache
def get_engine() -> Engine:
    """Engine síncrona do worker (usuário `data`: escreve em `market`)."""
    return create_engine(get_settings().data_database_url, pool_pre_ping=True, pool_size=2)


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


@dataclass(slots=True)
class JobContext:
    """O que o miolo do job recebe: sessão aberta, período e o contador de linhas."""

    name: str
    period: date | None
    session: Session
    rows: int = 0
    notes: dict[str, Any] = field(default_factory=dict)

    def wrote(self, count: int) -> int:
        self.rows += count
        return count


@contextmanager
def lock(name: str, *, ttl: int = LOCK_TTL_SECONDS) -> Iterator[None]:
    """Lock distribuído com TTL. Ocupado → `JobSkipped` (não é erro: é concorrência)."""
    client = get_redis()
    key = f"{LOCK_PREFIX}{name}"
    token = secrets.token_hex(16)
    if not client.set(key, token, nx=True, ex=ttl):
        raise JobSkipped(f"{name}: outro processo já está rodando (lock ocupado)")
    try:
        yield
    finally:
        client.eval(_RELEASE_SCRIPT, 1, key, token)


def check_source_allowed(session: Session, source: str) -> None:
    """ADR-017: em produção, fonte sem termos verificados não roda.

    A checagem é no banco, não em constante do código: quando a licença da B3 sair, o
    desbloqueio é uma linha em `data_sources` (registrada em `fontes-de-dados.md`), não
    um deploy.
    """
    if not get_settings().is_prod:
        return
    row = session.execute(
        select(DataSource.terms_checked_at).where(DataSource.source == source)
    ).first()
    if row is None:
        raise JobSkipped(f"fonte {source!r} não está em data_sources — cadastrar antes de rodar")
    if row[0] is None:
        raise JobSkipped(
            f"fonte {source!r} sem termos verificados (ADR-017): bloqueada em produção"
        )


@contextmanager
def run(
    name: str,
    *,
    period: date | None = None,
    source: str | None = None,
    use_lock: bool = True,
) -> Iterator[JobContext]:
    """Executa um job: lock, `etl_runs`, sessão e fechamento garantido.

    O `period` é a unidade de trabalho (o pregão, o mês do informe, o ano da DFP) e
    entra no lock: dois anos diferentes podem ser reprocessados em paralelo, o mesmo
    ano não.
    """
    lock_name = f"{name}:{period.isoformat()}" if period else name
    started = datetime.now(UTC)
    session_factory = sessionmaker(get_engine(), expire_on_commit=False)

    with session_factory() as session:
        etl_run = EtlRun(job=name, period=period, started_at=started, status="running")
        session.add(etl_run)
        session.commit()

        context = JobContext(name=name, period=period, session=session)
        status, error = "success", None
        try:
            with _maybe_lock(lock_name, enabled=use_lock):
                if source is not None:
                    check_source_allowed(session, source)
                yield context
                session.commit()
        except JobSkipped as skipped:
            session.rollback()
            status, error = "skipped", str(skipped)
            logger.info("%s: %s", name, skipped)
        except Exception as failure:
            session.rollback()
            status, error = "failed", f"{type(failure).__name__}: {failure}"
            logger.exception("%s falhou", name)
            raise
        else:
            logger.info("%s: %d linhas em %s", name, context.rows, _elapsed(started))
        finally:
            # No `finally` de propósito: sucesso, pulo ou falha, a linha de `etl_runs`
            # é sempre fechada — é dela que sai o alerta de frescor.
            _finish(session, etl_run, status, error, context.rows)


@contextmanager
def _maybe_lock(name: str, *, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return
    with lock(name):
        yield


def _finish(session: Session, etl_run: EtlRun, status: str, error: str | None, rows: int) -> None:
    etl_run.status = status
    etl_run.error = error
    etl_run.rows = rows
    etl_run.finished_at = datetime.now(UTC)
    session.add(etl_run)
    session.commit()


def _elapsed(started: datetime) -> str:
    return f"{(datetime.now(UTC) - started).total_seconds():.1f}s"


def main(entrypoint: Any) -> None:
    """Roda um job da linha de comando (`python -m alpherion.data.jobs.<job>`).

    Sai com código 1 em falha para o cron do host enxergar; `skipped` é saída 0 — não
    rodar por lock ou por licença é comportamento esperado, não incidente.
    """
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    entrypoint()
