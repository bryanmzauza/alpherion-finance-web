"""Fórmulas dos indicadores e extração do plano de contas da CVM.

A companhia de referência é inventada e com números redondos, para que cada indicador
possa ser conferido de cabeça. O que os testes fixam não é o valor — é a regra: ausência
vira `null` **com motivo**, denominador ≤ 0 não vira indicador, e nada disso vira zero.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from alpherion.data.transform.cvm_accounts import Fundamentals, extract, latest_period
from alpherion.data.transform.cvm_statements import ANNUAL, StatementRow
from alpherion.data.transform.indicators import (
    FORMULAS_VERSION,
    TAX_RATE,
    cagr,
    compute,
    dividends_per_share_12m,
)

PERIODO = date(2025, 12, 31)


def _row(
    statement: str, code: str, name: str, value: str | None, *, con: bool = True
) -> StatementRow:
    return StatementRow(
        cvm_code=99999,
        period_end=PERIODO,
        period_type=ANNUAL,
        statement=statement,
        consolidated=con,
        account_code=code,
        account_name=name,
        value=Decimal(value) if value is not None else None,
        version=1,
        period_start=date(2025, 1, 1) if statement in {"dre", "dfc"} else None,
    )


#: Companhia com números redondos: receita 1.000, lucro 100, PL 500, dívida líquida 200.
LINHAS = [
    _row("dre", "3.01", "Receita de Venda de Bens e/ou Serviços", "1000"),
    _row("dre", "3.03", "Resultado Bruto", "400"),
    _row("dre", "3.05", "Resultado Antes do Resultado Financeiro e dos Tributos", "200"),
    _row("dre", "3.11", "Lucro/Prejuízo Consolidado do Período", "120"),
    _row("dre", "3.11.01", "Atribuído a Sócios da Empresa Controladora", "100"),
    _row("bp_ativo", "1", "Ativo Total", "2000"),
    _row("bp_ativo", "1.01", "Ativo Circulante", "600"),
    _row("bp_ativo", "1.01.01", "Caixa e Equivalentes de Caixa", "80"),
    _row("bp_ativo", "1.01.02", "Aplicações Financeiras", "20"),
    _row("bp_passivo", "2.01", "Passivo Circulante", "300"),
    _row("bp_passivo", "2.01.04", "Empréstimos e Financiamentos", "100"),
    _row("bp_passivo", "2.02.01", "Empréstimos e Financiamentos", "200"),
    _row("bp_passivo", "2.03", "Patrimônio Líquido Consolidado", "500"),
    _row("dfc", "6.01", "Caixa Líquido Atividades Operacionais", "180"),
    _row("dfc", "6.01.01.02", "Depreciação e Amortização", "50"),
]


def _fundamentals(rows: list[StatementRow] | None = None) -> Fundamentals:
    return extract(
        rows if rows is not None else LINHAS,
        cvm_code=99999,
        period_end=PERIODO,
        period_type=ANNUAL,
        consolidated=True,
    )


# --- extração do plano de contas -------------------------------------------


def test_extrai_os_conceitos_do_plano_de_contas() -> None:
    f = _fundamentals()
    assert f.get("revenue") == Decimal("1000")
    assert f.get("ebit") == Decimal("200")
    assert f.get("equity") == Decimal("500")
    assert f.get("depreciation") == Decimal("50")


#: Itaú, DFP 2025 (valores em R$ bi): plano de contas de instituição financeira.
BANCO = [
    _row("dre", "3.01", "Receitas da Intermediação Financeira", "387.12"),
    _row("dre", "3.05", "Resultado Antes dos Tributos sobre o Lucro", "50.25"),
    _row("dre", "3.09", "Lucro/Prejuízo Consolidado do Período", "45.85"),
    _row("dre", "3.09.01", "Atribuído a Sócios da Empresa Controladora", "44.86"),
    _row("bp_ativo", "1", "Ativo Total", "3066.17"),
    _row("bp_ativo", "1.01", "Caixa e Equivalentes de Caixa", "37.14"),
    _row("bp_passivo", "2.01", "Passivos Financeiros ao Valor Justo através do Resultado", "71.4"),
    _row("bp_passivo", "2.03", "Passivos Financeiros ao Custo Amortizado", "2350.9"),
    _row("bp_passivo", "2.08", "Patrimônio Líquido Consolidado", "215.1"),
]


def test_banco_acha_patrimonio_e_lucro_pelo_nome() -> None:
    """No Itaú o PL é 2.08 e o lucro dos controladores 3.09.01 — não 2.03 nem 3.11."""
    f = _fundamentals(BANCO)
    assert f.get("equity") == Decimal("215.1")
    assert f.get("net_income") == Decimal("44.86")


def test_banco_nao_tem_circulante_nem_divida_e_diz_por_que() -> None:
    f = _fundamentals(BANCO)
    for conceito in ("current_liabilities", "current_assets", "cash", "debt_short", "ebit"):
        assert f.get(conceito) is None
        assert "instituição financeira" in f.missing[conceito]


def test_roe_do_banco_sai_com_o_patrimonio_certo() -> None:
    resultado = compute(_fundamentals(BANCO))
    assert resultado.values["roe"] == pytest.approx(Decimal("44.86") / Decimal("215.1"))
    assert resultado.values.get("current_ratio") is None


def test_lucro_dos_controladores_vence_o_consolidado() -> None:
    """Numa holding com minoritários, o consolidado infla ROE e LPA."""
    assert _fundamentals().get("net_income") == Decimal("100")


def test_divida_liquida_e_bruta_menos_caixa() -> None:
    f = _fundamentals()
    assert f.gross_debt == Decimal("300")
    assert f.cash_and_investments == Decimal("100")
    assert f.net_debt == Decimal("200")


def test_caixa_liquido_da_divida_negativa_e_e_valido() -> None:
    linhas = [r for r in LINHAS if r.account_code not in {"2.01.04", "2.02.01"}]
    linhas.append(_row("bp_passivo", "2.01.04", "Empréstimos e Financiamentos", "10"))
    f = _fundamentals(linhas)
    assert f.net_debt == Decimal("-90")


def test_depreciacao_e_achada_pelo_nome_na_dfc() -> None:
    """É o único número que a CVM não padroniza por código."""
    linhas = [r for r in LINHAS if "Deprecia" not in r.account_name]
    linhas.append(_row("dfc", "6.01.01.09", "Depreciações, amortizações e exaustão", "-50"))
    assert _fundamentals(linhas).get("depreciation") == Decimal("50"), "o sinal não pode decidir"


def test_conta_ausente_registra_o_motivo() -> None:
    linhas = [r for r in LINHAS if r.account_code != "3.01"]
    f = _fundamentals(linhas)
    assert f.get("revenue") is None
    assert "3.01" in f.missing["revenue"]


def test_escopos_nao_se_misturam() -> None:
    """Lucro consolidado sobre patrimônio individual daria um ROE inventado."""
    individual = [_row("bp_passivo", "2.03", "Patrimônio Líquido", "50", con=False)]
    f = _fundamentals([*LINHAS, *individual])
    assert f.get("equity") == Decimal("500")


def test_periodo_mais_recente() -> None:
    antigo = _row("dre", "3.01", "Receita", "900")
    antigo = replace(antigo, period_end=date(2024, 12, 31))
    assert latest_period([antigo, *LINHAS]) == PERIODO


# --- fórmulas ---------------------------------------------------------------


def test_indicadores_de_balanco_conferidos_a_mao() -> None:
    i = compute(_fundamentals())
    assert i["roe"] == Decimal("0.2")  # 100 / 500
    assert i["roa"] == Decimal("0.05")  # 100 / 2000
    assert i["gross_margin"] == Decimal("0.4")  # 400 / 1000
    assert i["net_margin"] == Decimal("0.1")  # 100 / 1000
    assert i["ebitda_margin"] == Decimal("0.25")  # (200 + 50) / 1000
    assert i["current_ratio"] == Decimal("2")  # 600 / 300
    assert i["net_debt_ebitda"] == Decimal("0.8")  # 200 / 250
    assert i["net_debt_equity"] == Decimal("0.4")  # 200 / 500


def test_roic_usa_nopat_sobre_capital_investido() -> None:
    """EBIT 200 × (1 − 34%) = 132, sobre PL 500 + dívida líquida 200."""
    i = compute(_fundamentals())
    assert i["roic"] == Decimal("200") * (Decimal(1) - TAX_RATE) / Decimal("700")
    assert i.inputs["tax_rate"] == str(TAX_RATE), "a premissa vai para a página"


def test_valuation_com_preco_e_acoes() -> None:
    i = compute(
        _fundamentals(),
        price=Decimal("20"),
        shares=Decimal("50"),
        dividends_12m_per_share=Decimal("1"),
    )
    assert i["eps"] == Decimal("2")  # 100 / 50
    assert i["bvps"] == Decimal("10")  # 500 / 50
    assert i["market_cap"] == Decimal("1000")  # 20 × 50
    assert i["pe"] == Decimal("10")  # 20 / 2
    assert i["pb"] == Decimal("2")  # 20 / 10
    assert i["psr"] == Decimal("1")  # 1000 / 1000
    assert i["ev_ebitda"] == Decimal("1200") / Decimal("250")
    assert i["ev_ebit"] == Decimal("6")  # 1200 / 200
    assert i["dy_12m"] == Decimal("0.05")  # 1 / 20
    assert i["payout"] == Decimal("0.5")  # 1 / 2


def test_sem_preco_os_indicadores_de_balanco_continuam_saindo() -> None:
    """ADR-017: sem a licença da B3 o pipeline roda e a página mostra o que não é preço."""
    i = compute(_fundamentals(), shares=Decimal("50"))
    assert i["roe"] == Decimal("0.2")
    assert i["eps"] == Decimal("2")
    assert i["pe"] is None
    assert "não licenciada" in i.missing["pe"]
    assert i["market_cap"] is None


def test_prejuizo_nao_vira_pl_negativo_na_tela() -> None:
    linhas = [r for r in LINHAS if r.account_code not in {"3.11", "3.11.01"}]
    linhas.append(_row("dre", "3.11", "Lucro/Prejuízo Consolidado do Período", "-100"))
    i = compute(_fundamentals(linhas), price=Decimal("20"), shares=Decimal("50"))
    assert i["pe"] is None, "P/L negativo lê-se como 'barato' e não significa nada"
    assert i.missing["pe"] == "lucro 12 m negativo"
    # ROE e margem negativos, ao contrário, são fato e vão para a página com o sinal.
    assert i["roe"] == Decimal("-0.2")
    assert i["net_margin"] == Decimal("-0.1")


def test_patrimonio_negativo_nao_vira_pvp() -> None:
    linhas = [r for r in LINHAS if r.account_code != "2.03"]
    linhas.append(_row("bp_passivo", "2.03", "Patrimônio Líquido Consolidado", "-50"))
    i = compute(_fundamentals(linhas), price=Decimal("20"), shares=Decimal("50"))
    assert i["pb"] is None
    assert i.missing["pb"] == "patrimônio líquido negativo"
    assert i.missing["roe"] == "patrimônio líquido negativo"


def test_sem_depreciacao_o_ebitda_fica_null_com_motivo() -> None:
    """Melhor "—" com motivo do que um EBITDA igual ao EBIT."""
    linhas = [r for r in LINHAS if "Deprecia" not in r.account_name]
    i = compute(_fundamentals(linhas))
    assert i["ebitda_margin"] is None
    assert i["net_debt_ebitda"] is None
    assert "DFC" in i.missing["ebitda_margin"]


def test_nenhum_indicador_ausente_vira_zero() -> None:
    vazio = Fundamentals(cvm_code=1, period_end=PERIODO, period_type=ANNUAL, consolidated=True)
    i = compute(vazio)
    assert set(i.values.values()) == {None}
    assert all(i.missing[name] for name in i.values), "toda ausência tem motivo"


def test_pvp_do_fii_usa_o_valor_patrimonial_da_cota() -> None:
    vazio = Fundamentals(cvm_code=1, period_end=PERIODO, period_type=ANNUAL, consolidated=True)
    i = compute(vazio, price=Decimal("104"), nav_per_share=Decimal("100"))
    assert i["pvp"] == Decimal("1.04")


def test_inputs_guardam_a_versao_das_formulas_e_as_entradas() -> None:
    i = compute(_fundamentals(), price=Decimal("20"), shares=Decimal("50"))
    assert i.inputs["formulas_version"] == FORMULAS_VERSION
    assert i.inputs["period_end"] == "2025-12-31"
    assert i.inputs["net_debt"] == "200"
    assert i.inputs["source"] == "CVM"


@pytest.mark.parametrize(
    ("inicio", "fim", "esperado"),
    [
        (Decimal("100"), Decimal("100"), Decimal("0")),
        (Decimal("-10"), Decimal("100"), None),  # saiu de prejuízo: taxa não existe
        (Decimal("0"), Decimal("100"), None),
        (Decimal("100"), None, None),
    ],
)
def test_cagr(inicio: Decimal, fim: Decimal | None, esperado: Decimal | None) -> None:
    resultado = cagr(inicio, fim, 5)
    if esperado is None:
        assert resultado is None
    else:
        assert resultado is not None
        assert abs(resultado - esperado) < Decimal("0.0001")


def test_cagr_de_dobro_em_cinco_anos() -> None:
    resultado = cagr(Decimal("100"), Decimal("200"), 5)
    assert resultado is not None
    assert abs(resultado - Decimal("0.1487")) < Decimal("0.0001")


def test_proventos_de_doze_meses_somam_so_o_que_e_caixa() -> None:
    proventos = [
        (Decimal("0.5"), True),  # dividendo
        (Decimal("0.3"), True),  # JCP
        (Decimal("0.2"), False),  # bonificação: muda quantidade, não caixa
        (None, True),
    ]
    assert dividends_per_share_12m(proventos) == Decimal("0.8")
    assert dividends_per_share_12m([]) is None
