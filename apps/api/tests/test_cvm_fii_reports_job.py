"""Informe de FII → ticker: o ISIN liga os dois, e às vezes dois fundos declaram o mesmo.

No informe de 2026, 133 pares (ISIN, mês) aparecem com dois CNPJs. A coluna
`Mercado_Negociacao_Bolsa` resolve parte; o resto fica sem informe naquele mês — pôr o
patrimônio de um fundo na página de outro seria pior que o "—".
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from alpherion.data.jobs.cvm_fii_reports import fii_segment_slug, pick_report
from alpherion.data.sources.cvm import FiiReportRow

BASE = FiiReportRow(
    cnpj="01657856000105",
    period=date(2026, 1, 1),
    version=1,
    nav=Decimal("100"),
    nav_per_share=None,
    shares=None,
    shareholders=None,
    income_per_share=None,
    vacancy_physical=None,
    vacancy_financial=None,
    admin_fee=None,
    manager=None,
    administrator=None,
    segment="Logística",
    isin="BRRTELCTF001",
)


def test_um_fundo_so_fica_a_maior_versao() -> None:
    escolhido = pick_report([BASE, replace(BASE, version=2, nav=Decimal("110"))])
    assert escolhido is not None and escolhido.version == 2


def test_dois_fundos_desempata_quem_negocia_em_bolsa() -> None:
    outro = replace(BASE, cnpj="43862625000175", exchange_listed=True)
    assert pick_report([replace(BASE, exchange_listed=False), outro]) == outro


def test_empate_sem_criterio_fica_sem_informe() -> None:
    outro = replace(BASE, cnpj="43862625000175")
    assert pick_report([BASE, outro]) is None


def test_slug_do_segmento_de_fii_nao_colide_com_o_da_b3() -> None:
    assert fii_segment_slug("Logística") == "fii-logistica"
