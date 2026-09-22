"""Parser das demonstrações da CVM (formato longo do DFP/ITR).

As fixtures são **sintéticas**: reproduzem o cabeçalho e as regras do formato (escala,
ordem de exercício, versão), com companhias inventadas. Nenhum arquivo da CVM no repo.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from alpherion.data.transform.cvm_statements import (
    ANNUAL,
    StatementRow,
    full_year_only,
    is_consolidated,
    latest_versions,
    parse_file,
    statement_of,
)

HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)


def _line(**over: str) -> str:
    fields = {
        "CNPJ_CIA": "00.000.000/0001-91",
        "DT_REFER": "2025-12-31",
        "VERSAO": "1",
        "DENOM_CIA": "COMPANHIA DE TESTE SA",
        "CD_CVM": "99999",
        "GRUPO_DFP": "DF Consolidado - Demonstração do Resultado",
        "MOEDA": "REAL",
        "ESCALA_MOEDA": "MIL",
        "ORDEM_EXERC": "ÚLTIMO",
        "DT_INI_EXERC": "2025-01-01",
        "DT_FIM_EXERC": "2025-12-31",
        "CD_CONTA": "3.01",
        "DS_CONTA": "Receita de Venda de Bens e/ou Serviços",
        "VL_CONTA": "1500000",
        "ST_CONTA_FIXA": "S",
    }
    fields.update(over)
    return ";".join(fields.values())


def _write(tmp_path: Path, name: str, *lines: str) -> Path:
    path = tmp_path / name
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="latin-1")
    return path


def test_nome_do_arquivo_define_demonstracao_e_escopo() -> None:
    assert statement_of("dfp_cia_aberta_DRE_con_2025.csv") == "dre"
    assert statement_of("dfp_cia_aberta_BPA_ind_2025.csv") == "bp_ativo"
    assert statement_of("itr_cia_aberta_DFC_MI_con_2025.csv") == "dfc"
    assert statement_of("dfp_cia_aberta_DVA_con_2025.csv") is None  # não carregamos DVA
    assert is_consolidated("dfp_cia_aberta_DRE_con_2025.csv") is True
    assert is_consolidated("dfp_cia_aberta_DRE_ind_2025.csv") is False


def test_escala_mil_vira_reais(tmp_path: Path) -> None:
    """R$ 1.500.000 mil = R$ 1,5 bilhão. Errar aqui erra todo indicador da empresa."""
    path = _write(tmp_path, "dfp_cia_aberta_DRE_con_2025.csv", _line())
    (row,) = list(parse_file(path, period_type=ANNUAL))
    assert row.value == Decimal("1500000000")
    assert row.cvm_code == 99999
    assert row.period_end == date(2025, 12, 31)
    assert row.statement == "dre"
    assert row.consolidated is True


def test_escala_unidade_nao_multiplica(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "dfp_cia_aberta_DRE_con_2025.csv",
        _line(ESCALA_MOEDA="UNIDADE", VL_CONTA="1500000"),
    )
    (row,) = list(parse_file(path, period_type=ANNUAL))
    assert row.value == Decimal("1500000")


def test_exercicio_anterior_e_descartado(tmp_path: Path) -> None:
    """O PENÚLTIMO já veio no pacote do ano dele, com a versão da época."""
    path = _write(
        tmp_path,
        "dfp_cia_aberta_DRE_con_2025.csv",
        _line(),
        _line(ORDEM_EXERC="PENÚLTIMO", DT_FIM_EXERC="2024-12-31", VL_CONTA="1000000"),
    )
    rows = list(parse_file(path, period_type=ANNUAL))
    assert [r.period_end for r in rows] == [date(2025, 12, 31)]


def test_republicacao_vence_a_versao_original(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "dfp_cia_aberta_DRE_con_2025.csv",
        _line(VERSAO="1", VL_CONTA="1500000"),
        _line(VERSAO="3", VL_CONTA="1400000"),
    )
    (row,) = latest_versions(parse_file(path, period_type=ANNUAL))
    assert row.version == 3
    assert row.value == Decimal("1400000000")


def test_valor_vazio_vira_none_e_nao_zero(tmp_path: Path) -> None:
    path = _write(tmp_path, "dfp_cia_aberta_DRE_con_2025.csv", _line(VL_CONTA=""))
    (row,) = list(parse_file(path, period_type=ANNUAL))
    assert row.value is None


def test_moeda_estrangeira_e_ignorada(tmp_path: Path) -> None:
    path = _write(tmp_path, "dfp_cia_aberta_DRE_con_2025.csv", _line(MOEDA="DOLAR"))
    assert list(parse_file(path, period_type=ANNUAL)) == []


def test_arquivo_que_nao_carregamos_nao_rende_linha(tmp_path: Path) -> None:
    path = _write(tmp_path, "dfp_cia_aberta_DVA_con_2025.csv", _line())
    assert list(parse_file(path, period_type=ANNUAL)) == []


def test_balanco_nao_tem_inicio_de_exercicio(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "dfp_cia_aberta_BPA_con_2025.csv",
        _line(DT_INI_EXERC="", CD_CONTA="1", DS_CONTA="Ativo Total"),
    )
    (row,) = list(parse_file(path, period_type=ANNUAL))
    assert row.period_start is None
    assert row.months is None
    assert list(full_year_only([row])) == [row]


@pytest.mark.parametrize(
    ("start", "end", "mantem"),
    [
        (date(2025, 1, 1), date(2025, 12, 31), True),  # exercício cheio
        (date(2025, 10, 1), date(2025, 12, 31), False),  # só o 4º trimestre
        (date(2025, 1, 1), date(2025, 9, 30), False),  # acumulado até setembro
    ],
)
def test_dfp_fica_so_com_o_exercicio_cheio(start: date, end: date, mantem: bool) -> None:
    row = StatementRow(
        cvm_code=99999,
        period_end=end,
        period_type=ANNUAL,
        statement="dre",
        consolidated=True,
        account_code="3.01",
        account_name="Receita",
        value=Decimal("1"),
        version=1,
        period_start=start,
    )
    assert (list(full_year_only([row])) == [row]) is mantem
