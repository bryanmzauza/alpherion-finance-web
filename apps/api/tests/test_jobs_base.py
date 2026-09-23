"""Bordas de todo job do pipeline: lock, `etl_runs`, licença e idempotência.

Sem banco e sem Redis de verdade: o que se testa aqui é a regra de operação — lock
ocupado não é erro, falha fecha a linha de `etl_runs` mesmo assim, e fonte sem termos
verificados não roda em produção (ADR-017). O miolo de cada job tem teste próprio na
camada de `sources`/`transform`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from alpherion.data.jobs import base
from alpherion.db.upsert import upsert


class FakeRedis:
    """O bastante de Redis para o lock: `set(nx, ex)` e o script de liberação."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def eval(self, _script: str, _numkeys: int, key: str, token: str) -> int:
        if self.store.get(key) == token:
            del self.store[key]
            return 1
        return 0


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis()
    monkeypatch.setattr(base, "get_redis", lambda: client)
    return client


# --- lock -------------------------------------------------------------------


def test_lock_e_solto_no_fim(fake_redis: FakeRedis) -> None:
    with base.lock("cotahist_daily"):
        assert fake_redis.store
    assert not fake_redis.store, "lock preso travaria o job até o TTL expirar"


def test_lock_ocupado_nao_e_erro_e_sim_pulo(fake_redis: FakeRedis) -> None:
    """Cron disparando sobre um job que ainda roda é rotina, não incidente."""
    with (
        base.lock("cotahist_daily"),
        pytest.raises(base.JobSkipped, match="lock ocupado"),
        base.lock("cotahist_daily"),
    ):
        pass  # pragma: no cover - o lock de cima impede chegar aqui


def test_lock_so_e_solto_por_quem_o_pegou(fake_redis: FakeRedis) -> None:
    """Entre o TTL expirar e o DEL, o lock pode já ser de outro worker."""
    with base.lock("job"):
        fake_redis.store["alpherion:job:job"] = "token-de-outro-worker"
    assert fake_redis.store["alpherion:job:job"] == "token-de-outro-worker"


def test_jobs_de_periodos_diferentes_nao_disputam_o_mesmo_lock(fake_redis: FakeRedis) -> None:
    with base.lock("cvm_statements:2024"), base.lock("cvm_statements:2025"):
        assert len(fake_redis.store) == 2


# --- licença (ADR-017) ------------------------------------------------------


class FakeResult:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def first(self) -> tuple[Any, ...] | None:
        return self._row


class FakeSession:
    def __init__(self, row: tuple[Any, ...] | None) -> None:
        self._row = row

    def execute(self, _statement: Any) -> FakeResult:
        return FakeResult(self._row)


def _prod(monkeypatch: pytest.MonkeyPatch, *, is_prod: bool) -> None:
    class Settings:
        pass

    settings = Settings()
    settings.is_prod = is_prod  # type: ignore[attr-defined]
    monkeypatch.setattr(base, "get_settings", lambda: settings)


def test_fonte_sem_termos_nao_roda_em_producao(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch, is_prod=True)
    with pytest.raises(base.JobSkipped, match="sem termos verificados"):
        base.check_source_allowed(FakeSession((None,)), "b3")  # type: ignore[arg-type]


def test_fonte_com_termos_verificados_roda(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch, is_prod=True)
    base.check_source_allowed(FakeSession((date(2026, 9, 21),)), "cvm")  # type: ignore[arg-type]


def test_fonte_desconhecida_e_pulo_com_motivo(monkeypatch: pytest.MonkeyPatch) -> None:
    _prod(monkeypatch, is_prod=True)
    with pytest.raises(base.JobSkipped, match="cadastrar antes de rodar"):
        base.check_source_allowed(FakeSession(None), "fonte_nova")  # type: ignore[arg-type]


def test_em_dev_a_fonte_bloqueada_roda(monkeypatch: pytest.MonkeyPatch) -> None:
    """Processar não é distribuir (ADR-017): o pipeline é construído normalmente."""
    _prod(monkeypatch, is_prod=False)
    base.check_source_allowed(FakeSession((None,)), "b3")  # type: ignore[arg-type]


# --- upsert -----------------------------------------------------------------


class RecordingSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(statement)


def test_upsert_sem_linhas_nao_toca_no_banco() -> None:
    session = RecordingSession()
    assert upsert(session, _Model(), []) == 0  # type: ignore[arg-type]
    assert session.statements == []


def test_upsert_quebra_em_lotes() -> None:
    """Lote único de 1.200 linhas estouraria o limite de parâmetros do Postgres."""
    from alpherion.db.models import MacroSeries

    session = RecordingSession()
    rows = [{"series": "cdi", "date": date(2026, 1, 1), "value": i} for i in range(1200)]
    enviadas = upsert(session, MacroSeries, rows)  # type: ignore[arg-type]

    assert enviadas == 1200
    assert len(session.statements) == 3  # 500 + 500 + 200


def test_upsert_atualiza_no_conflito() -> None:
    from alpherion.db.models import MacroSeries

    session = RecordingSession()
    upsert(
        session,  # type: ignore[arg-type]
        MacroSeries,
        [{"series": "cdi", "date": date(2026, 1, 1), "value": 1}],
    )
    sql = str(session.statements[0]).lower()
    assert "on conflict" in sql
    assert "do update" in sql


class _Model:
    """Placeholder para o caminho "sem linhas", que nem chega a olhar a tabela."""


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])


def test_anotacoes_do_job_vao_para_etl_runs() -> None:
    """A documentação dos jobs promete as anotações em `etl_runs`; antes, elas se perdiam."""
    from datetime import date as _date
    from decimal import Decimal as _Decimal
    from unittest.mock import MagicMock

    from alpherion.data.jobs.base import _finish
    from alpherion.db.models import EtlRun

    execucao = EtlRun(job="x", status="running")
    _finish(
        MagicMock(),
        execucao,
        "success",
        None,
        10,
        {"papeis_por_tipo": {"stock": 841}, "dia": _date(2026, 9, 22), "v": _Decimal("1.5")},
    )
    assert execucao.notes == {"papeis_por_tipo": {"stock": 841}, "dia": "2026-09-22", "v": "1.5"}


def test_sem_anotacoes_a_coluna_fica_nula() -> None:
    from unittest.mock import MagicMock

    from alpherion.data.jobs.base import _finish
    from alpherion.db.models import EtlRun

    execucao = EtlRun(job="x", status="running")
    _finish(MagicMock(), execucao, "success", None, 0, {})
    assert execucao.notes is None
