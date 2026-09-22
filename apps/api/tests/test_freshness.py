"""Alerta de frescor do pipeline.

O modo de falha que este alerta existe para pegar é o **silêncio**: um job que para de
rodar não quebra nada visível — a página continua no ar com o número de ontem. Por isso
os testes cobrem sobretudo o que *não* deve alertar, que é onde um alerta barulhento
perde a utilidade.
"""

from __future__ import annotations

import datetime as dt

import pytest

from alpherion.data.freshness import (
    COTAHIST_DEADLINE_HOUR,
    FAILURE_STREAK,
    Level,
    Run,
    evaluate,
    is_business_day,
)

QUARTA_21H = dt.datetime(2026, 9, 23, 21, 30, tzinfo=dt.UTC)
SABADO_21H = dt.datetime(2026, 9, 26, 21, 30, tzinfo=dt.UTC)


def _run(job: str, status: str, *, day: dt.datetime) -> Run:
    return Run(job=job, status=status, started_at=day, period=day.date())


# --- cotação do dia ---------------------------------------------------------


def test_sem_cotahist_depois_das_21h_alerta() -> None:
    relatorio = evaluate([], now=QUARTA_21H)
    assert relatorio.level is Level.WARNING
    assert relatorio.findings[0].job == "cotahist_daily"
    assert "não entrou" in relatorio.findings[0].message


def test_cotahist_carregado_nao_alerta() -> None:
    runs = [_run("cotahist_daily", "success", day=QUARTA_21H)]
    assert evaluate(runs, now=QUARTA_21H).ok


def test_antes_das_21h_nao_alerta() -> None:
    """O job roda às 19h30; alertar às 18h seria alertar por nada."""
    cedo = QUARTA_21H.replace(hour=COTAHIST_DEADLINE_HOUR - 3)
    assert evaluate([], now=cedo).ok


def test_fim_de_semana_nao_alerta() -> None:
    """Não houve pregão: não há o que carregar."""
    assert evaluate([], now=SABADO_21H).ok
    assert not is_business_day(SABADO_21H.date())


def test_job_pulado_nao_alerta() -> None:
    """Feriado: o job baixou 404 e terminou como `skipped`. Não é incidente."""
    runs = [_run("cotahist_daily", "skipped", day=QUARTA_21H)]
    assert evaluate(runs, now=QUARTA_21H).ok


def test_falha_de_hoje_alerta_no_mesmo_dia() -> None:
    """Para a cotação, uma falha já basta: é o dado que mais rapidamente envelhece."""
    runs = [_run("cotahist_daily", "failed", day=QUARTA_21H)]
    assert evaluate(runs, now=QUARTA_21H).level is Level.WARNING


# --- fontes instáveis (dois dias) -------------------------------------------


@pytest.mark.parametrize("job", ["cvm_documents", "b3_index_composition"])
def test_uma_falha_nao_alerta(job: str) -> None:
    """Fonte externa cai. Alertar na primeira falha treina todo mundo a ignorar."""
    runs = [
        _run("cotahist_daily", "success", day=QUARTA_21H),
        _run(job, "failed", day=QUARTA_21H),
    ]
    assert evaluate(runs, now=QUARTA_21H).ok


@pytest.mark.parametrize("job", ["cvm_documents", "b3_index_composition"])
def test_duas_falhas_seguidas_alertam(job: str) -> None:
    runs = [
        _run("cotahist_daily", "success", day=QUARTA_21H),
        _run(job, "failed", day=QUARTA_21H),
        _run(job, "failed", day=QUARTA_21H - dt.timedelta(days=1)),
    ]
    relatorio = evaluate(runs, now=QUARTA_21H)
    assert relatorio.level is Level.WARNING
    assert relatorio.findings[0].job == job
    assert f"{FAILURE_STREAK} dias seguidos" in relatorio.findings[0].message


def test_duas_falhas_no_mesmo_dia_nao_sao_dois_dias() -> None:
    """Retry do mesmo dia não é uma sequência — seria alerta em cima de um incidente só."""
    runs = [
        _run("cotahist_daily", "success", day=QUARTA_21H),
        _run("cvm_documents", "failed", day=QUARTA_21H),
        _run("cvm_documents", "failed", day=QUARTA_21H - dt.timedelta(hours=2)),
    ]
    assert evaluate(runs, now=QUARTA_21H).ok


def test_sucesso_no_meio_zera_a_contagem() -> None:
    """O problema se resolveu sozinho; não há o que reportar."""
    ontem = QUARTA_21H - dt.timedelta(days=1)
    runs = [
        _run("cotahist_daily", "success", day=QUARTA_21H),
        _run("cvm_documents", "failed", day=QUARTA_21H),
        _run("cvm_documents", "failed", day=ontem),
        _run("cvm_documents", "success", day=ontem + dt.timedelta(hours=1)),
    ]
    assert evaluate(runs, now=QUARTA_21H).ok


def test_falhas_antigas_nao_contam() -> None:
    antigo = QUARTA_21H - dt.timedelta(days=10)
    runs = [
        _run("cotahist_daily", "success", day=QUARTA_21H),
        _run("cvm_documents", "failed", day=antigo),
        _run("cvm_documents", "failed", day=antigo - dt.timedelta(days=1)),
    ]
    assert evaluate(runs, now=QUARTA_21H).ok


# --- mensagem ---------------------------------------------------------------


def test_mensagem_diz_o_job_e_o_runbook() -> None:
    texto = evaluate([], now=QUARTA_21H).as_text()
    assert "cotahist_daily" in texto
    assert "reprocessar-job.md" in texto


def test_tudo_certo_tem_mensagem_curta() -> None:
    """Silêncio é o resultado normal — o job nem manda esta mensagem."""
    runs = [_run("cotahist_daily", "success", day=QUARTA_21H)]
    assert evaluate(runs, now=QUARTA_21H).as_text() == "Pipeline do Alpherion: tudo carregado."


def test_varios_problemas_no_mesmo_relatorio() -> None:
    runs = [
        _run("cvm_documents", "failed", day=QUARTA_21H),
        _run("cvm_documents", "failed", day=QUARTA_21H - dt.timedelta(days=1)),
        _run("b3_index_composition", "failed", day=QUARTA_21H),
        _run("b3_index_composition", "failed", day=QUARTA_21H - dt.timedelta(days=1)),
    ]
    relatorio = evaluate(runs, now=QUARTA_21H)
    assert {f.job for f in relatorio.findings} == {
        "cotahist_daily",
        "cvm_documents",
        "b3_index_composition",
    }
