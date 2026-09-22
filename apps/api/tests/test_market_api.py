"""Rotas de mercado e a trava de licença do ADR-017.

Sem banco: o repositório é substituído por funções que devolvem modelos prontos. O que
se testa aqui é o **contrato** — que é onde as regras do produto vivem:

- todo bloco de número sai com a sua fonte (`SourceBadge` depende disso);
- sem licença da B3, preço sai `null` **com motivo**, nunca zero e nunca sumido;
- o motivo verdadeiro de uma ausência ("empresa não publicou DFP") não é apagado pela
  trava;
- ordenação fora da lista fechada é 422, não uma cláusula SQL;
- sem token ou sem escopo, nada sai.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from decimal import Decimal
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alpherion.db.session import get_session
from alpherion.market import repository, schemas
from alpherion.market.flags import CRYPTO_REASON, PRICE_REASON, Gate
from alpherion.settings import Settings

from .conftest import IMPORTS_TOKEN, READONLY_TOKEN, WEB_TOKEN

FONTE = schemas.SourceRef(source="b3", attribution="Fonte: B3", document="COTAHIST")
FONTE_CVM = schemas.SourceRef(source="cvm", attribution="Fonte: CVM", document="DFP 2025")

DETALHE = schemas.SecurityDetail(
    profile=schemas.SecurityProfile(
        source=schemas.SourceRef(source="b3", attribution="Fonte: B3"),
        ticker="PETR4",
        type="stock",
        company_name="PETROLEO BRASILEIRO S.A. PETROBRAS",
        sector_slug="petroleo-gas-e-biocombustiveis",
        status="active",
    ),
    price=schemas.PriceHeader(
        source=FONTE,
        ticker="PETR4",
        price=Decimal("38.50"),
        change_percent_day=Decimal("0.012"),
        volume=Decimal("1200000000"),
        quote_date=dt.date(2026, 9, 18),
    ),
    indicators=schemas.Indicators(
        source=FONTE_CVM,
        date=dt.date(2026, 9, 18),
        pe=Decimal("6.2"),
        roe=Decimal("0.21"),
        market_cap=Decimal("500000000000"),
        missing_reasons={"ev_ebitda": "empresa não publicou DFP 2025"},
    ),
)


def _headers(token: str = WEB_TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def market_client(client: TestClient) -> Iterator[TestClient]:
    """Cliente com a sessão do banco trocada por um dublê — as rotas não chegam nela."""

    async def fake_session() -> Any:
        return None

    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_session] = fake_session
    yield client
    app.dependency_overrides.clear()


def _stub(monkeypatch: pytest.MonkeyPatch, name: str, value: Any) -> None:
    async def fake(*_args: object, **_kwargs: object) -> Any:
        return value

    monkeypatch.setattr(repository, name, fake)


# --- auth -------------------------------------------------------------------


def test_sem_token_nao_sai_nada(market_client: TestClient) -> None:
    assert market_client.get("/v1/securities/PETR4").status_code == 401


def test_token_sem_o_escopo_e_403(market_client: TestClient) -> None:
    """`imports:write` não dá acesso a dado de mercado: cada cliente vê só o que precisa."""
    resposta = market_client.get("/v1/securities/PETR4", headers=_headers(IMPORTS_TOKEN))
    assert resposta.status_code == 403
    assert "market:read" in resposta.json()["detail"]


def test_token_com_market_read_passa(
    market_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(monkeypatch, "get_security", DETALHE)
    resposta = market_client.get("/v1/securities/PETR4", headers=_headers(READONLY_TOKEN))
    assert resposta.status_code == 200


# --- fonte em todo bloco ----------------------------------------------------


def test_cada_bloco_traz_a_sua_fonte(
    market_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cadastro vem da B3, indicador da CVM: uma fonte só daria a impressão errada."""
    _stub(monkeypatch, "get_security", DETALHE)
    corpo = market_client.get("/v1/securities/PETR4", headers=_headers()).json()

    assert corpo["profile"]["source"]["attribution"] == "Fonte: B3"
    assert corpo["indicators"]["source"]["attribution"] == "Fonte: CVM"
    assert corpo["indicators"]["source"]["document"] == "DFP 2025"


def test_papel_inexistente_e_404(
    market_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(monkeypatch, "get_security", None)
    assert market_client.get("/v1/securities/XXXX9", headers=_headers()).status_code == 404


# --- ordenação --------------------------------------------------------------


def test_ordenacao_fora_da_lista_fechada_e_422(market_client: TestClient) -> None:
    resposta = market_client.get(
        "/v1/securities", params={"sort": "preco_justo"}, headers=_headers()
    )
    assert resposta.status_code == 422
    assert "Aceitas" in resposta.json()["detail"]


def test_ordem_padrao_e_neutra() -> None:
    """Liquidez: alfabética privilegiaria o começo do alfabeto; valuation insinuaria nota."""
    assert repository.DEFAULT_SORT == "volume"


def test_nenhuma_ordenacao_expressa_juizo_de_valor() -> None:
    proibidos = {"score", "nota", "rank", "ranking", "preco_justo", "recomendacao", "upside"}
    assert not proibidos & set(repository.SORTABLE)


def test_pagina_nao_passa_de_cem(market_client: TestClient) -> None:
    resposta = market_client.get("/v1/securities", params={"page_size": 500}, headers=_headers())
    assert resposta.status_code == 422, "o teto de 100 é do contrato (§2.3)"


# --- trava do ADR-017 -------------------------------------------------------


def test_gate_zera_o_preco_e_diz_o_motivo() -> None:
    gate = Gate(Settings(market_b3_prices_enabled=False))
    travado = gate.apply(DETALHE.price)

    assert travado.price is None, "sem licença, preço não sai"
    assert travado.missing_reasons["price"] == PRICE_REASON
    assert travado.ticker == "PETR4", "o resto do bloco continua"


def test_gate_nao_apaga_o_motivo_verdadeiro() -> None:
    """ "Empresa não publicou DFP" é informação melhor que "fonte não licenciada"."""
    travado = Gate(Settings(market_b3_prices_enabled=False)).apply(DETALHE.indicators)

    assert travado.missing_reasons["ev_ebitda"] == "empresa não publicou DFP 2025"
    assert travado.missing_reasons["pe"] == PRICE_REASON


def test_gate_preserva_o_que_nao_depende_de_preco() -> None:
    """ADR-017: ROE, margens e endividamento saem sem licença nenhuma."""
    travado = Gate(Settings(market_b3_prices_enabled=False)).apply(DETALHE.indicators)

    assert travado.roe == Decimal("0.21")
    assert travado.pe is None
    assert travado.market_cap is None


def test_gate_liberado_nao_mexe_em_nada() -> None:
    liberado = Gate(Settings(market_b3_prices_enabled=True)).apply(DETALHE.price)
    assert liberado.price == Decimal("38.50")
    assert liberado.missing_reasons == {}


def test_gate_de_cripto_e_independente_do_de_acoes() -> None:
    gate = Gate(Settings(market_b3_prices_enabled=True, market_crypto_enabled=False))
    travado = gate.apply(DETALHE.price, crypto=True)
    assert travado.price is None
    assert travado.missing_reasons["price"] == CRYPTO_REASON


def test_gate_nao_muta_o_original() -> None:
    """O mesmo objeto pode vir de um cache: mutar vazaria a trava para outra resposta."""
    Gate(Settings(market_b3_prices_enabled=False)).apply(DETALHE.price)
    assert DETALHE.price.price == Decimal("38.50")


def test_modelo_sem_campo_de_preco_passa_intacto() -> None:
    perfil = Gate(Settings(market_b3_prices_enabled=False)).apply(DETALHE.profile)
    assert perfil.company_name == DETALHE.profile.company_name


# --- listas e documentos ----------------------------------------------------


def test_lista_pagina_e_devolve_total(
    market_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pagina = schemas.Page[schemas.SecuritySummary](
        items=[
            schemas.SecuritySummary(
                ticker="PETR4", type="stock", company_name="PETROBRAS", price=Decimal("38.50")
            )
        ],
        total=1,
        page=1,
        page_size=50,
    )
    _stub(monkeypatch, "list_securities", pagina)
    corpo = market_client.get("/v1/securities", headers=_headers()).json()

    assert corpo["total"] == 1
    assert corpo["items"][0]["ticker"] == "PETR4"


def test_comunicado_sai_com_link_e_sem_resumo(
    market_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§8.3: o produto lista e linka; resumir fato relevante seria interpretação."""
    pagina = schemas.Page[schemas.Document](
        items=[
            schemas.Document(
                protocol="123456",
                category="Fato Relevante",
                subject="Aquisição de ativo",
                delivered_at=dt.date(2026, 9, 18),
                url="https://dados.cvm.gov.br/documento/123456",
            )
        ],
        total=1,
        page=1,
        page_size=50,
    )
    _stub(monkeypatch, "documents", pagina)
    documento = market_client.get("/v1/securities/PETR4/documents", headers=_headers()).json()[
        "items"
    ][0]

    assert documento["url"].startswith("https://dados.cvm.gov.br/")
    assert set(documento) == {
        "protocol",
        "category",
        "type",
        "subject",
        "delivered_at",
        "reference_date",
        "url",
    }, "nenhum campo de texto do documento no contrato"


def test_historia_respeita_o_intervalo(market_client: TestClient) -> None:
    resposta = market_client.get(
        "/v1/securities/PETR4/history", params={"range": "10a"}, headers=_headers()
    )
    assert resposta.status_code == 422, "intervalo é de lista fechada"


def test_busca_exige_dois_caracteres(market_client: TestClient) -> None:
    assert (
        market_client.get("/v1/assets/search", params={"q": "p"}, headers=_headers()).status_code
        == 422
    )
