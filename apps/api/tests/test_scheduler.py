"""Agendamento do worker `data`.

O que importa aqui não é o horário — é a **ordem** e a robustez: preço antes de ajuste,
ajuste antes de indicadores, indicadores antes de revalidar a página. E um job que
falha não pode derrubar o agendador, senão uma indisponibilidade da B3 às 19h30 deixa
o pipeline parado até alguém perceber.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from alpherion.data import scheduler
from alpherion.data.jobs.base import JobSkipped

SEGUNDA = datetime(2026, 9, 21, 12, 0, tzinfo=scheduler.TZ)
SABADO = datetime(2026, 9, 26, 12, 0, tzinfo=scheduler.TZ)


def _entry(name: str) -> scheduler.Scheduled:
    return next(e for e in scheduler.SCHEDULE if e.name == name)


def _hora(entry: scheduler.Scheduled) -> tuple[int, int]:
    return entry.hour, entry.minute


def test_preco_vem_antes_do_ajuste_e_dos_indicadores() -> None:
    """Indicador calculado antes do preço do dia sai com a cotação de ontem."""
    assert _hora(_entry("cotahist_daily")) < _hora(_entry("adjust_factors"))
    assert _hora(_entry("adjust_factors")) < _hora(_entry("indicators_rebuild"))
    assert _hora(_entry("indicators_rebuild")) < _hora(_entry("revalidate_pages"))


def test_eventos_vem_antes_do_ajuste() -> None:
    """Um provento que chega depois do ajuste só entra no gráfico no dia seguinte."""
    assert _hora(_entry("b3_corporate_actions")) < _hora(_entry("adjust_factors"))


def test_cotahist_so_roda_em_dia_util() -> None:
    entry = _entry("cotahist_daily")
    assert entry.due(SEGUNDA.replace(hour=entry.hour, minute=entry.minute))
    assert not entry.due(SABADO.replace(hour=entry.hour, minute=entry.minute))


def test_job_mensal_so_no_dia_marcado() -> None:
    entry = _entry("cvm_statements")
    assert entry.day_of_month is not None
    na_hora = SEGUNDA.replace(day=entry.day_of_month, hour=entry.hour, minute=entry.minute)
    assert entry.due(na_hora)
    assert not entry.due(na_hora.replace(day=entry.day_of_month + 1))


def test_fora_do_minuto_nao_dispara() -> None:
    entry = _entry("bcb_series")
    assert not entry.due(SEGUNDA.replace(hour=entry.hour, minute=entry.minute + 1))


def test_falha_de_um_job_nao_derruba_o_agendador(monkeypatch: pytest.MonkeyPatch) -> None:
    chamados: list[str] = []

    def explode() -> None:
        chamados.append("falhou")
        raise RuntimeError("fonte fora do ar")

    def pula() -> None:
        chamados.append("pulou")
        raise JobSkipped("lock ocupado")

    def ok() -> None:
        chamados.append("ok")

    agora = SEGUNDA.replace(hour=19, minute=30)
    fake: tuple[Any, ...] = (
        scheduler.Scheduled("a", explode, hour=19, minute=30),
        scheduler.Scheduled("b", pula, hour=19, minute=30),
        scheduler.Scheduled("c", ok, hour=19, minute=30),
    )
    monkeypatch.setattr(scheduler, "SCHEDULE", fake)

    assert scheduler.run_due(agora) == ["a", "b", "c"]
    assert chamados == ["falhou", "pulou", "ok"]


def test_todo_job_agendado_existe_e_e_chamavel() -> None:
    for entry in scheduler.SCHEDULE:
        assert callable(entry.entrypoint), entry.name


def test_cripto_roda_de_tres_em_tres_horas() -> None:
    horas = sorted(e.hour for e in scheduler.SCHEDULE if e.name == "coingecko_prices")
    assert horas == list(range(0, 24, 3))
