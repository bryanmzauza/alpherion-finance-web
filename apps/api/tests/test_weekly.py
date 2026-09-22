"""Números da Leitura de Mercado.

O que estes testes prendem é a matemática, conferida contra casos calculados à mão e
contra o comportamento do `pandas` (que o script de vídeo usa). O risco aqui não é o
número explodir — é ele sair **plausível e errado**: uma volatilidade anualizada com o
fator trocado erra ~20% e ninguém nota olhando.
"""

from __future__ import annotations

import datetime as dt
import math
from decimal import Decimal

import pytest

from alpherion.market.weekly import (
    MIN_POINTS,
    TRADING_DAYS_CRYPTO,
    TRADING_DAYS_STOCK,
    Series,
    correlation,
    extremes,
    pct_change,
    snapshot,
    volatilities,
    volatility,
)

REFERENCIA = dt.date(2026, 9, 21)


def _serie(key: str, valores: list[float], *, crypto: bool = False) -> Series:
    inicio = REFERENCIA - dt.timedelta(days=len(valores) - 1)
    return Series(
        key=key,
        label=key.upper(),
        points=[(inicio + dt.timedelta(days=i), Decimal(str(v))) for i, v in enumerate(valores)],
        crypto=crypto,
    )


# --- variação ---------------------------------------------------------------


def test_variacao_conferida_a_mao() -> None:
    assert pct_change(Decimal("110"), Decimal("100")) == pytest.approx(0.10)
    assert pct_change(Decimal("90"), Decimal("100")) == pytest.approx(-0.10)


def test_sem_um_dos_dois_pontos_a_variacao_e_none() -> None:
    """Nunca zero: zero diria "não variou", o que não foi medido."""
    assert pct_change(Decimal("110"), None) is None
    assert pct_change(None, Decimal("100")) is None
    assert pct_change(Decimal("110"), Decimal("0")) is None


def test_snapshot_usa_o_ultimo_fechamento_ate_a_data() -> None:
    """Fim de semana e feriado não têm pregão: vale o último fechamento anterior."""
    serie = _serie("ibovespa", [100, 101, 102, 103, 104, 105, 106, 110])
    (mudanca,) = snapshot([serie], reference=REFERENCIA)

    assert mudanca.price == Decimal("110")
    assert mudanca.change_7d == pytest.approx(0.10)  # 110 sobre 100


def test_serie_vazia_vira_motivo_e_nao_zero() -> None:
    vazia = Series(key="x", label="X", points=[])
    (mudanca,) = snapshot([vazia], reference=REFERENCIA)

    assert mudanca.price is None
    assert mudanca.change_7d is None
    assert mudanca.missing_reason == "série sem dado na data"


# --- correlação -------------------------------------------------------------


def test_series_identicas_tem_correlacao_um() -> None:
    a = [0.01, -0.02, 0.03, 0.00, 0.015, -0.005, 0.02, -0.01, 0.005, 0.01, 0.02]
    assert correlation(a, a) == pytest.approx(1.0)


def test_series_opostas_tem_correlacao_menos_um() -> None:
    a = [0.01, -0.02, 0.03, 0.00, 0.015, -0.005, 0.02, -0.01, 0.005, 0.01, 0.02]
    assert correlation(a, [-x for x in a]) == pytest.approx(-1.0)


def test_correlacao_confere_com_o_calculo_de_pandas() -> None:
    """Pearson à mão dá o mesmo que `Series.corr()` — a conta está escrita, não importada."""
    a = [0.01, 0.02, -0.01, 0.03, 0.00, 0.015, -0.02, 0.005, 0.01, -0.005, 0.02, 0.01]
    b = [0.02, 0.01, 0.00, 0.02, 0.01, 0.010, -0.01, 0.000, 0.02, 0.005, 0.01, 0.02]

    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    esperado = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True)) / math.sqrt(
        sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)
    )
    assert correlation(a, b) == pytest.approx(esperado)


def test_poucos_pontos_nao_viram_correlacao() -> None:
    """Correlação de três dias é ruído com aparência de fato — e iria para o vídeo."""
    curto = [0.01] * (MIN_POINTS - 1)
    assert correlation(curto, curto) is None


def test_serie_constante_nao_tem_correlacao_definida() -> None:
    constante = [0.0] * 20
    variavel = [0.01 * i for i in range(20)]
    assert correlation(constante, variavel) is None


# --- volatilidade -----------------------------------------------------------


def test_volatilidade_anualizada_a_mao() -> None:
    retornos = [0.01, -0.01] * 10
    esperado = math.sqrt(sum((r - 0.0) ** 2 for r in retornos) / (len(retornos) - 1)) * math.sqrt(
        TRADING_DAYS_STOCK
    )
    assert volatility(retornos, crypto=False) == pytest.approx(esperado)


def test_cripto_anualiza_por_365_e_bolsa_por_252() -> None:
    """Cripto negocia todo dia. Trocar o fator erra ~20% e continua parecendo plausível."""
    retornos = [0.01, -0.01] * 10
    bolsa = volatility(retornos, crypto=False)
    cripto = volatility(retornos, crypto=True)

    assert bolsa is not None and cripto is not None
    assert cripto / bolsa == pytest.approx(math.sqrt(TRADING_DAYS_CRYPTO / TRADING_DAYS_STOCK))


def test_volatilidade_com_poucos_pontos_e_none() -> None:
    assert volatility([0.01] * (MIN_POINTS - 1), crypto=False) is None


def test_volatilidades_por_janela() -> None:
    serie = _serie("ibovespa", [100 + i * (1 if i % 2 else -1) for i in range(300)])
    (resultado,) = volatilities([serie], reference=REFERENCIA)

    assert set(resultado.windows) == {30, 90, 252}
    assert all(value is not None for value in resultado.windows.values())


# --- extremos ---------------------------------------------------------------


def test_extremos_da_janela_de_52_semanas() -> None:
    serie = _serie("bitcoin", [100, 350, 80, 120], crypto=True)
    minimo, maximo = extremes(serie, reference=REFERENCIA)

    assert minimo == Decimal("80")
    assert maximo == Decimal("350")


def test_extremos_de_serie_vazia() -> None:
    assert extremes(Series(key="x", label="X", points=[]), reference=REFERENCIA) == (None, None)
