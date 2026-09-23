"""Fontes da B3 (listagem, índices, eventos) e do CoinGecko.

Os endpoints da B3 não são documentados e podem mudar sem aviso — por isso o que se
testa aqui é o **comportamento diante da mudança**: resposta em HTML e carteira vazia
viram falha explícita (para o job usar o fallback), rótulo novo vira `None` com aviso,
e nenhum dos dois vira "a B3 não tem nada hoje".
"""

from __future__ import annotations

import base64
import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from alpherion.data.sources import b3_events, b3_indices, b3_listing, coingecko
from alpherion.data.sources.b3_api import (
    LISTED_BASE,
    B3UnavailableError,
    build_url,
    encode,
    fetch_pages,
)
from alpherion.data.sources.http import ALLOWED_HOSTS, SourceError, check_host


def _client(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


# --- cliente da B3 ----------------------------------------------------------


def test_parametros_vao_em_base64_no_caminho() -> None:
    """É como a B3 espera: o JSON dos parâmetros vira um segmento da URL."""
    encoded = encode({"language": "pt-br", "pageNumber": 1})
    assert json.loads(base64.b64decode(encoded)) == {"language": "pt-br", "pageNumber": 1}


def test_url_montada_aponta_para_host_permitido() -> None:
    url = build_url(LISTED_BASE, b3_listing.COMPANIES_PATH, {"language": "pt-br"})
    check_host(url)  # não levanta


def test_host_inexistente_nao_esta_na_lista() -> None:
    """ "sistemaswebb3-indices" não existe no DNS; os índices ficam no host da listagem."""
    assert "sistemaswebb3-indices.b3.com.br" not in ALLOWED_HOSTS
    assert "sistemaswebb3-listados.b3.com.br" in ALLOWED_HOSTS


def test_resposta_html_vira_falha_e_nao_lista_vazia() -> None:
    """Bloqueio por WAF devolve HTML; silenciar isso apagaria dado no banco."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>erro</html>")

    with pytest.raises(B3UnavailableError, match="não é JSON"):
        fetch_pages(LISTED_BASE, b3_listing.COMPANIES_PATH, {}, http=_client(handler))


def test_json_codificado_duas_vezes_e_desembrulhado() -> None:
    """`GetListedSupplementCompany` devolve uma string com o JSON dentro."""
    from alpherion.data.sources.b3_api import fetch_json

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json.dumps([{"code": "PETR"}]))

    assert fetch_json(f"{LISTED_BASE}/x/y", http=_client(handler)) == [{"code": "PETR"}]


def test_paginacao_percorre_todas_as_paginas() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        params = json.loads(base64.b64decode(str(request.url).rsplit("/", 1)[-1]))
        page = params["pageNumber"]
        return httpx.Response(
            200,
            json={"page": {"totalPages": 3}, "results": [{"code": f"AAAA{page}"}]},
        )

    records = fetch_pages(LISTED_BASE, "x/y", {}, http=_client(handler))
    assert [r["code"] for r in records] == ["AAAA1", "AAAA2", "AAAA3"]


# --- índices ----------------------------------------------------------------


def test_peso_da_carteira_vira_fracao() -> None:
    """8,124% → 0,08124: a tabela e o cálculo de concentração usam fração."""
    membros = b3_indices.parse_portfolio(
        [{"cod": "PETR4", "asset": "PETROBRAS", "part": "8,124", "theoricalQty": "1.234.567"}],
        slug="ibovespa",
        reference_date=date(2026, 9, 2),
    )
    assert membros[0].weight == Decimal("0.08124")
    assert membros[0].theoretical_quantity == Decimal("1234567")
    assert membros[0].reference_date == date(2026, 9, 2)


def _portfolio_client(results: list[dict[str, object]], header_date: str | None) -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        header = {"date": header_date} if header_date else {}
        return httpx.Response(
            200, json={"page": {"totalPages": 1}, "header": header, "results": results}
        )

    return _client(handler)


def test_carteira_vazia_e_erro_e_nao_indice_sem_papeis() -> None:
    """Gravar vazio apagaria a composição inteira e a página mostraria um índice oco."""
    with pytest.raises(B3UnavailableError, match="manter a última conhecida"):
        b3_indices.fetch_composition("ibovespa", http=_portfolio_client([], "23/09/26"))


def test_carteira_leva_a_data_que_a_b3_informa() -> None:
    """A data é parte do dado: a do cabeçalho da B3, não a do dia em que o job rodou."""
    membros = b3_indices.fetch_composition(
        "ibovespa",
        http=_portfolio_client([{"cod": "PETR4", "part": "8,124"}], "02/09/26"),
    )
    assert membros[0].reference_date == date(2026, 9, 2)


def test_carteira_sem_data_e_erro() -> None:
    with pytest.raises(B3UnavailableError, match="sem data"):
        b3_indices.fetch_composition(
            "ibovespa", http=_portfolio_client([{"cod": "PETR4", "part": "8,1"}], None)
        )


def test_indice_desconhecido_e_erro_de_programacao() -> None:
    with pytest.raises(ValueError, match="índice desconhecido"):
        b3_indices.fetch_composition("nasdaq")


def test_todos_os_indices_do_portal_estao_mapeados() -> None:
    assert set(b3_indices.INDICES) >= {"ibovespa", "ifix", "idiv", "smll"}


# Trecho real da grade de 2026 do Ibovespa ("Estatísticas históricas"): linha = dia,
# rateValueN = mês N; célula vazia é dia sem pregão.
GRADE_IBOV = {
    "results": [
        {"day": 1, "rateValue1": None, "rateValue9": "179.722,48"},
        {"day": 2, "rateValue1": "160.538,69", "rateValue9": "185.205,09"},
        {"day": 31, "rateValue2": None, "rateValue1": "181.708,23"},
    ]
}


def test_grade_anual_vira_fechamentos_em_ordem() -> None:
    fechamentos = b3_indices.parse_year_closes(GRADE_IBOV, slug="ibovespa", year=2026)
    assert [f.date for f in fechamentos] == [
        date(2026, 1, 2),
        date(2026, 1, 31),
        date(2026, 9, 1),
        date(2026, 9, 2),
    ]
    assert fechamentos[0].close == Decimal("160538.69")


def test_variacao_e_fracao_sobre_o_fechamento_anterior() -> None:
    fechamentos = b3_indices.with_changes(
        b3_indices.parse_year_closes(GRADE_IBOV, slug="ibovespa", year=2026),
        previous=Decimal("160000"),
    )
    assert fechamentos[0].change_percent == Decimal("160538.69") / Decimal("160000") - 1
    ultimo = fechamentos[-1]
    assert ultimo.change_percent == Decimal("185205.09") / Decimal("179722.48") - 1


def test_primeiro_dia_sem_fechamento_anterior_fica_sem_variacao() -> None:
    fechamentos = b3_indices.with_changes(
        b3_indices.parse_year_closes(GRADE_IBOV, slug="ibovespa", year=2026)
    )
    assert fechamentos[0].change_percent is None, "sem anterior, None — nunca zero"


def test_grade_em_formato_inesperado_e_erro() -> None:
    with pytest.raises(B3UnavailableError, match="formato inesperado"):
        b3_indices.parse_year_closes({"erro": "x"}, slug="ibovespa", year=2026)


# --- eventos corporativos ---------------------------------------------------


@pytest.mark.parametrize(
    ("rotulo", "esperado"),
    [
        ("DIVIDENDO", "dividend"),
        ("Juros sobre Capital Próprio", "jcp"),
        ("Rendimento", "fii_income"),
        ("Desdobramento", "split"),
        ("Grupamento", "reverse_split"),
        ("Bonificação", "bonus"),
        ("Coisa Nova Que a B3 Inventou", None),
    ],
)
def test_rotulo_do_evento(rotulo: str, esperado: str | None) -> None:
    assert b3_events.kind_of(rotulo) == esperado


def test_provento_com_data_e_valor() -> None:
    evento = b3_events.parse_event(
        {
            "label": "DIVIDENDO",
            "lastDatePrior": "12/11/2026",
            "paymentDate": "30/11/2026",
            "valueCash": "0,35",
        },
        ticker="petr4",
    )
    assert evento is not None
    assert evento.ticker == "PETR4"
    assert evento.kind == "dividend"
    assert evento.ex_date == date(2026, 11, 12)
    assert evento.payment_date == date(2026, 11, 30)
    assert evento.value_per_share == Decimal("0.35")
    assert evento.source == "b3"


def test_evento_sem_data_nao_entra_na_agenda() -> None:
    assert (
        b3_events.parse_event({"label": "DIVIDENDO", "valueCash": "0,35"}, ticker="PETR4") is None
    )


def test_evento_de_rotulo_desconhecido_e_ignorado() -> None:
    registro = {"label": "EVENTO NOVO", "lastDatePrior": "12/11/2026"}
    assert b3_events.parse_event(registro, ticker="PETR4") is None


def test_desdobramento_vira_proporcao_que_o_ajuste_entende() -> None:
    """A B3 publica o percentual de ações novas; `adjust.py` espera "antigas:novas"."""
    evento = b3_events.parse_event(
        {"label": "Desdobramento", "lastDatePrior": "12/11/2026", "factor": "100"},
        ticker="PETR4",
    )
    assert evento is not None
    assert evento.ratio == "1:2"

    from alpherion.data.transform.adjust import Event, event_factor

    fator = event_factor(Event(evento.ex_date or date.today(), "split", ratio=evento.ratio), None)
    assert fator == Decimal("0.5")


@pytest.mark.parametrize(
    ("rotulo", "fator", "proporcao", "fator_de_ajuste"),
    [
        # Magalu: desdobramento de 2020 (1:4) e grupamento de 2024 (10:1), fatores da B3.
        ("DESDOBRAMENTO", "300,00000000000", "1:4", Decimal("0.25")),
        ("GRUPAMENTO", "0,10000000000", "1:0.1", Decimal("10")),
        ("BONIFICACAO", "5,00000000000", "5%", None),
    ],
)
def test_fator_da_b3_vira_a_proporcao_certa(
    rotulo: str, fator: str, proporcao: str, fator_de_ajuste: Decimal | None
) -> None:
    from alpherion.data.transform.adjust import Event, event_factor

    evento = b3_events.parse_event(
        {"label": rotulo, "lastDatePrior": "13/10/2020", "factor": fator}, ticker="MGLU3"
    )
    assert evento is not None and evento.ratio == proporcao
    if fator_de_ajuste is not None:
        assert event_factor(Event(date(2020, 10, 13), evento.kind, ratio=proporcao), None) == (
            fator_de_ajuste
        )


# Trecho real de GetListedSupplementCompany para PETR (23/09/2026).
SUPLEMENTO_PETR = [
    {
        "code": "PETR",
        "cashDividends": [
            {
                "assetIssued": "BRPETRACNOR9",
                "paymentDate": "21/12/2026",
                "rate": "0,47156696000",
                "isinCode": "BRPETRACNOR9",
                "label": "DIVIDENDO",
                "lastDatePrior": "21/08/2026",
            },
            {
                "assetIssued": "BRPETRACNPR6",
                "paymentDate": "23/11/2026",
                "rate": "0,67407131000",
                "isinCode": "BRPETRACNPR6",
                "label": "JRS CAP PROPRIO",
                "lastDatePrior": "21/08/2026",
            },
            {
                "assetIssued": "BRPETRDBS036",
                "paymentDate": "01/01/2026",
                "rate": "1,0",
                "isinCode": "BRPETRDBS036",
                "label": "DIVIDENDO",
                "lastDatePrior": "01/12/2025",
            },
        ],
        "stockDividends": [],
        "subscriptions": [],
    }
]


def test_eventos_do_emissor_vao_para_o_ticker_dono_do_isin() -> None:
    eventos = b3_events.parse_supplement(
        SUPLEMENTO_PETR, {"BRPETRACNOR9": "PETR3", "BRPETRACNPR6": "PETR4"}
    )
    assert [(e.ticker, e.kind) for e in eventos] == [("PETR3", "dividend"), ("PETR4", "jcp")]
    assert eventos[1].value_per_share == Decimal("0.67407131000")
    assert eventos[1].payment_date == date(2026, 11, 23)
    # ISIN fora do cadastro (debênture no exemplo) não vira evento.


# --- CoinGecko --------------------------------------------------------------


def test_cotacao_de_cripto_em_reais() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "id": "bitcoin",
                    "symbol": "btc",
                    "name": "Bitcoin",
                    "current_price": 350000.55,
                    "market_cap": 7000000000000,
                    "total_volume": 120000000000,
                    "price_change_percentage_24h": -1.25,
                    "circulating_supply": 19800000,
                    "last_updated": "2026-09-22T12:00:00.000Z",
                }
            ],
        )

    (ativo,) = coingecko.fetch_markets(http=_client(handler))
    assert ativo.asset_id == "bitcoin"
    assert ativo.symbol == "BTC"
    assert ativo.price == Decimal("350000.55")
    assert ativo.change_24h == Decimal("-0.0125"), "pontos percentuais viram fração"
    assert ativo.updated_at is not None


def test_limite_de_requisicoes_e_dito_com_todas_as_letras() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    with pytest.raises(SourceError, match="limite de requisições"):
        coingecko.fetch_markets(http=_client(handler))


def test_historico_junta_as_tres_series_por_dia() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "prices": [[1758499200000, 350000.0], [1758585600000, 352000.0]],
                "market_caps": [[1758499200000, 7e12]],
                "total_volumes": [],
            },
        )

    pontos = coingecko.fetch_history("bitcoin", http=_client(handler))
    assert len(pontos) == 2
    assert pontos[0].price == Decimal("350000.0")
    assert pontos[1].market_cap is None, "dia sem valor fica sem valor, não com zero"
    assert pontos[0].date < pontos[1].date


def test_historico_ignora_ponto_sem_preco() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"prices": [[1758499200000, None], [1758585600000, 1.0]]})

    assert len(coingecko.fetch_history("bitcoin", http=_client(handler))) == 1
