"""Ajuste do histórico por proventos e eventos (`transform/adjust.py`).

Casos calculados à mão: é a coluna que o gráfico de 5 anos e a rentabilidade do raio-x
leem, e um erro aqui aparece como uma queda que nunca existiu.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from alpherion.data.transform.adjust import Event, adjust, event_factor, parse_ratio

SERIE = [
    (date(2026, 3, 2), Decimal("100")),
    (date(2026, 3, 3), Decimal("100")),
    (date(2026, 3, 4), Decimal("50")),
    (date(2026, 3, 5), Decimal("52")),
]


@pytest.mark.parametrize(
    ("raw", "esperado"),
    [
        ("1:2", Decimal(2)),  # cada ação vira 2
        ("2:1", Decimal("0.5")),  # grupamento
        ("10%", Decimal("0.10")),
        ("1,5", Decimal("1.5")),
        ("", None),
        ("0:5", None),
        ("qualquer coisa", None),
    ],
)
def test_proporcao_do_evento(raw: str, esperado: Decimal | None) -> None:
    assert parse_ratio(raw) == esperado


def test_desdobramento_nao_vira_queda_no_grafico() -> None:
    """1:2 em 04/03: a série cai de 100 para 50 sem ninguém perder nada."""
    eventos = [Event(ex_date=date(2026, 3, 4), kind="split", ratio="1:2")]
    ajustada = adjust(SERIE, eventos)

    assert [q.adj_factor for q in ajustada] == [
        Decimal("0.5"),
        Decimal("0.5"),
        Decimal(1),
        Decimal(1),
    ]
    assert [q.close_adjusted for q in ajustada] == [
        Decimal("50.0"),
        Decimal("50.0"),
        Decimal("50"),
        Decimal("52"),
    ]


def test_grupamento_multiplica_o_preco_antigo() -> None:
    serie = [
        (date(2026, 3, 2), Decimal("10")),
        (date(2026, 3, 3), Decimal("100")),
    ]
    ajustada = adjust(serie, [Event(ex_date=date(2026, 3, 3), kind="reverse_split", ratio="10:1")])
    assert ajustada[0].close_adjusted == Decimal("100")
    assert ajustada[1].adj_factor == Decimal(1)


def test_dividendo_ajusta_pelo_fechamento_cum() -> None:
    """R$ 2 sobre fechamento cum de R$ 100 → fator 0,98 nos dias anteriores."""
    eventos = [
        Event(ex_date=date(2026, 3, 4), kind="dividend", value_per_share=Decimal("2")),
    ]
    ajustada = adjust(SERIE, eventos)
    assert ajustada[0].adj_factor == Decimal("0.98")
    assert ajustada[1].adj_factor == Decimal("0.98")
    assert ajustada[2].adj_factor == Decimal(1), "no dia ex o preço já está ex"


def test_eventos_se_acumulam_na_ordem() -> None:
    eventos = [
        Event(ex_date=date(2026, 3, 3), kind="dividend", value_per_share=Decimal("2")),
        Event(ex_date=date(2026, 3, 4), kind="split", ratio="1:2"),
    ]
    ajustada = adjust(SERIE, eventos)
    # 02/03 sofre os dois; 03/03 só o desdobramento (o dividendo já é ex nesse dia).
    assert ajustada[0].adj_factor == Decimal("0.98") * Decimal("0.5")
    assert ajustada[1].adj_factor == Decimal("0.5")


def test_ultimo_dia_sempre_tem_fator_um() -> None:
    """O ajuste é relativo ao preço de hoje — é o que torna o gráfico comparável."""
    eventos = [Event(ex_date=date(2026, 3, 4), kind="split", ratio="1:2")]
    assert adjust(SERIE, eventos)[-1].adj_factor == Decimal(1)
    assert adjust(SERIE, eventos)[-1].close_adjusted == Decimal("52")


def test_bonificacao_de_dez_por_cento() -> None:
    fator = event_factor(Event(date(2026, 3, 4), "bonus", ratio="10%"), Decimal("100"))
    assert fator == Decimal(1) / Decimal("1.1")


def test_subscricao_nao_ajusta_preco() -> None:
    assert (
        event_factor(Event(date(2026, 3, 4), "subscription", ratio="1:1"), Decimal("100")) is None
    )


def test_evento_sem_preco_cum_e_ignorado() -> None:
    """Série que começa depois do evento: ajustar por preço errado é pior que não ajustar."""
    eventos = [Event(ex_date=date(2026, 3, 2), kind="dividend", value_per_share=Decimal("2"))]
    ajustada = adjust(SERIE, eventos)
    assert all(q.adj_factor == Decimal(1) for q in ajustada)


def test_provento_maior_que_o_preco_e_ignorado() -> None:
    """Acontece (redução de capital, FII em liquidação) e inverteria a série inteira."""
    eventos = [
        Event(ex_date=date(2026, 3, 4), kind="dividend", value_per_share=Decimal("150")),
    ]
    assert all(q.adj_factor == Decimal(1) for q in adjust(SERIE, eventos))


def test_evento_fora_da_janela_nao_muda_nada() -> None:
    eventos = [Event(ex_date=date(2027, 1, 4), kind="split", ratio="1:2")]
    assert all(q.adj_factor == Decimal(1) for q in adjust(SERIE, eventos))


def test_serie_vazia() -> None:
    assert adjust([], [Event(date(2026, 3, 4), "split", ratio="1:2")]) == []


def test_serie_fora_de_ordem_e_ordenada() -> None:
    fora_de_ordem = list(reversed(SERIE))
    ajustada = adjust(fora_de_ordem, [])
    assert [q.date for q in ajustada] == [d for d, _ in SERIE]
