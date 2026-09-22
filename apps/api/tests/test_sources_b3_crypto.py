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


def test_host_dos_indices_esta_na_lista() -> None:
    assert "sistemaswebb3-indices.b3.com.br" in ALLOWED_HOSTS


def test_resposta_html_vira_falha_e_nao_lista_vazia() -> None:
    """Bloqueio por WAF devolve HTML; silenciar isso apagaria dado no banco."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>erro</html>")

    with pytest.raises(B3UnavailableError, match="não é JSON"):
        fetch_pages(LISTED_BASE, b3_listing.COMPANIES_PATH, {}, http=_client(handler))


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


# --- listagem ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("ticker", "hint", "esperado"),
    [
        ("PETR4", None, "stock"),
        ("VALE3", None, "stock"),
        ("SANB11", "unit", "unit"),
        ("BOVA11", "etf", "etf"),
        ("MXRF11", "fii", "fii"),
        ("MXRF11", None, "other"),  # 11 sem origem: não chutar a classe
        ("AAPL34", None, "bdr"),
        ("ABCD", None, "other"),
        ("lixo", None, "other"),
    ],
)
def test_tipo_do_papel_pelo_sufixo(ticker: str, hint: str | None, esperado: str) -> None:
    assert b3_listing.type_of(ticker, hint=hint) == esperado


def test_uma_companhia_rende_um_papel_por_ticker() -> None:
    registro = {
        "companyName": "PETROLEO BRASILEIRO S.A. PETROBRAS",
        "tradingName": "PETROBRAS",
        "codes": ["PETR3", "PETR4"],
        "cnpj": "33.000.167/0001-01",
        "codeCVM": "9512",
        "sectorName": "Petróleo, Gás e Biocombustíveis",
        "subSectorName": "Petróleo, Gás e Biocombustíveis",
        "segmentName": "Exploração e/ou Refino",
    }
    papeis = list(b3_listing.parse_company(registro))
    assert [p.ticker for p in papeis] == ["PETR3", "PETR4"]
    assert papeis[0].cnpj == "33000167000101"
    assert papeis[0].cvm_code == 9512
    assert papeis[0].sector_slug is not None
    assert papeis[0].sector_slug.startswith("petroleo-gas-e-biocombustiveis")


def test_slug_do_setor_sem_acento_e_sem_pontuacao() -> None:
    assert b3_listing.slugify("Petróleo, Gás e Biocombustíveis") == "petroleo-gas-e-biocombustiveis"
    assert b3_listing.slugify(None, "  ") is None


def test_fundo_sem_digito_recebe_o_11() -> None:
    fundo = b3_listing.parse_fund({"acronym": "MXRF", "fundName": "MAXI RENDA"}, kind="fii")
    assert fundo is not None
    assert fundo.ticker == "MXRF11"
    assert fundo.type == "fii"


def test_registro_incompleto_nao_vira_papel() -> None:
    assert b3_listing.parse_fund({"acronym": "MXRF"}, kind="fii") is None
    assert list(b3_listing.parse_company({"companyName": "SEM TICKER"})) == []


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


def test_carteira_vazia_e_erro_e_nao_indice_sem_papeis() -> None:
    """Gravar vazio apagaria a composição inteira e a página mostraria um índice oco."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"page": {"totalPages": 1}, "results": []})

    with pytest.raises(B3UnavailableError, match="manter a última conhecida"):
        b3_indices.fetch_composition("ibovespa", http=_client(handler))


def test_indice_desconhecido_e_erro_de_programacao() -> None:
    with pytest.raises(ValueError, match="índice desconhecido"):
        b3_indices.fetch_composition("nasdaq")


def test_todos_os_indices_do_portal_estao_mapeados() -> None:
    assert set(b3_indices.INDICES) >= {"ibovespa", "ifix", "idiv", "smll"}


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
    assert ativo.change_24h == Decimal("-1.25")
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
