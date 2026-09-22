"""Plano da carga inicial (`data/backfill.py`).

O que estes testes protegem é a **ordem**, que é a única parte do backfill capaz de
produzir um banco silenciosamente errado: cadastro antes de tudo, preço e eventos antes
do ajuste, ajuste antes dos indicadores. E a robustez: uma etapa que falha não pode
abortar as outras — num backfill de horas, recomeçar do zero por causa de uma fonte
instável é o que faz ninguém rodar de novo.
"""

from __future__ import annotations

import pytest

from alpherion.data import backfill
from alpherion.data.jobs.base import JobSkipped


def _names(profile: backfill.Profile) -> list[str]:
    return [step.name for step in backfill.plan(profile)]


def _position(names: list[str], prefix: str) -> int:
    return next(i for i, name in enumerate(names) if name.startswith(prefix))


@pytest.mark.parametrize("profile", [backfill.SAMPLE, backfill.FULL])
def test_cadastro_vem_antes_de_tudo(profile: backfill.Profile) -> None:
    """Sem `securities` não há a que prender cotação, evento ou indicador."""
    names = _names(profile)
    assert names[0] == "b3_listing"
    assert _position(names, "cvm_companies") < _position(names, "cotahist")


@pytest.mark.parametrize("profile", [backfill.SAMPLE, backfill.FULL])
def test_ajuste_depois_do_preco_e_dos_eventos(profile: backfill.Profile) -> None:
    names = _names(profile)
    assert _position(names, "cotahist") < _position(names, "adjust_factors")
    assert _position(names, "b3_corporate_actions") < _position(names, "adjust_factors")


@pytest.mark.parametrize("profile", [backfill.SAMPLE, backfill.FULL])
def test_derivados_por_ultimo(profile: backfill.Profile) -> None:
    names = _names(profile)
    assert _position(names, "adjust_factors") < _position(names, "indicators_rebuild")
    assert names[-1] == "market_events_rebuild"


def test_amostra_cobre_todas_as_classes() -> None:
    """Toda tela precisa de dado de verdade — inclusive ETF e BDR."""
    assert len(backfill.SAMPLE_STOCKS) == 20
    assert len(backfill.SAMPLE_FIIS) == 10
    assert len(backfill.SAMPLE_ETFS) == 5
    assert len(backfill.SAMPLE_BDRS) == 5
    assert len(backfill.SAMPLE_INDICES) == 3
    assert len(set(backfill.SAMPLE.tickers)) == len(backfill.SAMPLE.tickers), "sem repetido"


def test_amostra_carrega_menos_anos_que_a_carga_completa() -> None:
    assert backfill.SAMPLE.quote_years < backfill.FULL.quote_years
    assert backfill.SAMPLE.tickers and not backfill.FULL.tickers


def test_amostra_filtra_os_papeis_no_cotahist() -> None:
    """O arquivo anual traz todo papel que já existiu; em dev, filtrar é o que o torna usável."""
    etapa = next(s for s in backfill.plan(backfill.SAMPLE) if s.name.startswith("cotahist"))
    assert "papéis" in etapa.notes

    etapa_full = next(s for s in backfill.plan(backfill.FULL) if s.name.startswith("cotahist"))
    assert etapa_full.notes == "ano inteiro"


def test_etapa_que_falha_nao_aborta_as_demais(monkeypatch: pytest.MonkeyPatch) -> None:
    executadas: list[str] = []

    def passo(name: str, erro: Exception | None = None) -> backfill.Step:
        def acao() -> None:
            executadas.append(name)
            if erro:
                raise erro

        return backfill.Step(name, acao)

    monkeypatch.setattr(
        backfill,
        "plan",
        lambda _profile: [
            passo("a"),
            passo("b", RuntimeError("fonte fora do ar")),
            passo("c", JobSkipped("fonte bloqueada (ADR-017)")),
            passo("d"),
        ],
    )

    report = backfill.run(backfill.SAMPLE)

    assert executadas == ["a", "b", "c", "d"]
    assert report.done == ["a", "d"]
    assert [name for name, _ in report.failed] == ["b"]
    assert [name for name, _ in report.skipped] == ["c"]
    assert not report.ok, "falha tem de virar código de saída 1"


def test_etapa_pulada_nao_e_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fonte bloqueada pelo ADR-017 é o estado esperado em produção, não incidente."""

    def bloqueada() -> None:
        raise JobSkipped("fonte 'b3' sem termos verificados")

    monkeypatch.setattr(backfill, "plan", lambda _p: [backfill.Step("b3_listing", bloqueada)])
    report = backfill.run(backfill.SAMPLE)
    assert report.ok
    assert report.skipped


def test_dry_run_nao_executa_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode() -> None:
        raise AssertionError("dry-run não pode executar a etapa")

    monkeypatch.setattr(backfill, "plan", lambda _p: [backfill.Step("x", explode)])
    assert backfill.run(backfill.SAMPLE, dry_run=True).done == ["x"]


def test_filtro_de_etapa(monkeypatch: pytest.MonkeyPatch) -> None:
    report = backfill.run(backfill.SAMPLE, only=["cotahist"], dry_run=True)
    assert report.done
    assert all(name.startswith("cotahist") for name in report.done)
