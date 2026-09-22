"""Parser do COTAHIST contra a fixture sintética (`tests/fixtures/cotahist/`)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from alpherion.data.transform.cotahist_parser import (
    RECORD_SIZE,
    CotahistError,
    Quote,
    parse_line,
    parse_lines,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cotahist" / "amostra.txt"


@pytest.fixture(scope="module")
def quotes() -> dict[str, Quote]:
    linhas = FIXTURE.read_text(encoding="latin-1").splitlines()
    return {q.ticker: q for q in parse_lines(linhas)}


def test_le_apenas_papeis_a_vista(quotes: dict[str, Quote]) -> None:
    """Opção, direito e papel sem negócio não viram linha na tabela."""
    assert set(quotes) == {"PETR4", "MXRF11", "BOVA11", "VALE3F", "ANTIGA3"}


def test_precos_com_duas_casas_implicitas(quotes: dict[str, Quote]) -> None:
    """`0000000004120` no arquivo é R$ 41,20 — não 4120."""
    petr = quotes["PETR4"]
    assert petr.close == Decimal("41.20")
    assert petr.open == Decimal("40.50")
    assert petr.high == Decimal("41.80")
    assert petr.low == Decimal("40.30")
    assert petr.average == Decimal("41.10")


def test_usa_decimal_e_nao_float(quotes: dict[str, Quote]) -> None:
    """Dinheiro em float acumula erro ao longo de 40 anos de série."""
    assert isinstance(quotes["PETR4"].close, Decimal)
    assert isinstance(quotes["PETR4"].volume, Decimal)


def test_volume_financeiro_e_quantidade(quotes: dict[str, Quote]) -> None:
    petr = quotes["PETR4"]
    assert petr.volume == Decimal("1234567.89")  # VOLTOT é (16)V99
    assert petr.quantity == 29970
    assert petr.trades == 15234


def test_fator_de_cotacao_normaliza_para_preco_unitario(quotes: dict[str, Quote]) -> None:
    """FATCOT 1000: R$ 12.500,00 por lote de mil = R$ 12,50 por ação.

    Sem isto, o histórico de um papel antigo dá um salto de mil vezes no dia em que a
    B3 mudou o fator — e o gráfico e o drawdown ficam errados.
    """
    antiga = quotes["ANTIGA3"]
    assert antiga.close == Decimal("12.50")
    assert antiga.open == Decimal("12.50")
    assert antiga.high == Decimal("12.60")
    # O volume financeiro não é afetado pelo fator: já vem em reais.
    assert antiga.volume == Decimal("37500.00")


def test_fii_e_etf_entram(quotes: dict[str, Quote]) -> None:
    """CODBDI 12 (FII) e 14 (certificados/ETF) são papéis que o site publica."""
    assert quotes["MXRF11"].close == Decimal("10.45")
    assert quotes["MXRF11"].codbdi == "12"
    assert quotes["BOVA11"].close == Decimal("128.90")


def test_mercado_fracionario_e_lido(quotes: dict[str, Quote]) -> None:
    """O fracionário (TPMERC 020) é o mesmo papel em lote menor; o ticker traz o F."""
    assert quotes["VALE3F"].tpmerc == "020"
    assert quotes["VALE3F"].close == Decimal("55.30")


def test_data_e_isin(quotes: dict[str, Quote]) -> None:
    assert quotes["PETR4"].date == date(2026, 9, 21)
    assert quotes["PETR4"].isin == "BRPETRACNPR6"
    assert quotes["BOVA11"].isin is None  # fixture sem ISIN


def test_registro_curto_e_erro() -> None:
    """Layout diferente do documentado = a B3 mudou o formato. Falhar alto."""
    with pytest.raises(CotahistError, match="245"):
        parse_line("01" + " " * 50)


def test_tipo_de_registro_desconhecido_e_erro() -> None:
    with pytest.raises(CotahistError, match="tipo de registro"):
        parse_line("77" + " " * (RECORD_SIZE - 2))


def test_header_e_trailer_sao_ignorados() -> None:
    assert parse_line("00" + " " * (RECORD_SIZE - 2)) is None
    assert parse_line("99" + " " * (RECORD_SIZE - 2)) is None
