"""Contrato comum dos jobs do pipeline.

Todo job é chamado pelo cron do host como `python -m alpherion.data.jobs.<job>`, e o
runbook e o alerta de frescor referem-se a ele pelo nome gravado em `etl_runs`. Estes
testes prendem esse contrato: módulo importável, `run()` presente, nome do job igual ao
nome do módulo (senão o alerta procura por um job que nunca aparece) e fonte declarada
nas cargas externas, que é o que aciona a trava do ADR-017.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

import pytest

import alpherion.data.jobs as jobs_package

#: Jobs que só leem o banco: não baixam nada, então não têm fonte a declarar.
DERIVED = frozenset(
    {
        "adjust_factors",
        "freshness_alert",
        "indicators_rebuild",
        "market_events_rebuild",
        "revalidate_pages",
    }
)


def _job_modules() -> list[str]:
    return sorted(
        module.name
        for module in pkgutil.iter_modules(jobs_package.__path__)
        if module.name != "base"
    )


def _load(name: str) -> ModuleType:
    return importlib.import_module(f"alpherion.data.jobs.{name}")


def test_ha_jobs_registrados() -> None:
    assert len(_job_modules()) >= 12


@pytest.mark.parametrize("name", _job_modules())
def test_job_tem_run_e_nome_igual_ao_modulo(name: str) -> None:
    module = _load(name)
    assert callable(module.run), f"{name}: sem `run()` — o cron não teria o que chamar"
    assert name == module.JOB, "o nome em `etl_runs` é o que o alerta de frescor procura"


@pytest.mark.parametrize("name", sorted(set(_job_modules()) - DERIVED))
def test_job_de_carga_declara_a_fonte(name: str) -> None:
    """Sem `SOURCE`, a trava de licença do ADR-017 não é consultada."""
    assert _load(name).SOURCE


@pytest.mark.parametrize("name", sorted(DERIVED))
def test_job_derivado_nao_declara_fonte(name: str) -> None:
    """Recalcular o que já está no banco não é distribuir nem baixar."""
    assert not hasattr(_load(name), "SOURCE")


def test_jobs_do_plano_existem() -> None:
    """A lista da §3.3 do plano — o que falta ainda não foi escrito, não esquecido."""
    esperados = {
        "cotahist_daily",
        "b3_listing",
        "b3_corporate_actions",
        "b3_index_composition",
        "cvm_companies",
        "cvm_statements",
        "cvm_fii_reports",
        "cvm_documents",
        "tesouro_daily",
        "bcb_series",
        "coingecko_prices",
        "coingecko_history",
        "adjust_factors",
        "indicators_rebuild",
        "market_events_rebuild",
        "revalidate_pages",
    }
    assert esperados <= set(_job_modules())
