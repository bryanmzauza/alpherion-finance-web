"""Rotas do portal: faixa, listas do dia, agenda, setores, índices, Tesouro e cripto.

O risco desta área não é o SQL — é a agregação virar opinião. Os testes prendem o que
impede isso: lista do dia declara a métrica **e** o piso de liquidez, contador é número
puro, carteira de índice sai sempre com a data, e a trava do ADR-017 vale por origem
(índice da B3 trava, Selic do BCB não, cripto tem trava própria).
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
from alpherion.market import market_data, repository, schemas
from alpherion.market.flags import CRYPTO_REASON, PRICE_REASON, Gate
from alpherion.settings import Settings

from .conftest import WEB_TOKEN

FONTE_B3 = schemas.SourceRef(source="b3", attribution="Fonte: B3")
FONTE_BCB = schemas.SourceRef(source="bcb", attribution="Fonte: Banco Central")
FONTE_CG = schemas.SourceRef(source="coingecko", attribution="Dados por CoinGecko")
FONTE_TESOURO = schemas.SourceRef(source="tesouro", attribution="Fonte: Tesouro Nacional")

FAIXA = [
    schemas.StripItem(
        source=FONTE_B3, key="ibovespa", label="Ibovespa", value=Decimal("142500"), unit="pts"
    ),
    schemas.StripItem(
        source=FONTE_BCB, key="selic_meta", label="Selic (meta)", value=Decimal("10.5"), unit="%"
    ),
    schemas.StripItem(
        source=FONTE_CG, key="bitcoin", label="Bitcoin", value=Decimal("350000"), unit="BRL"
    ),
]

ALTAS = schemas.MoversList(
    source=FONTE_B3,
    metric="change",
    direction="desc",
    min_volume=market_data.MIN_VOLUME_DEFAULT,
    items=[
        schemas.Mover(
            ticker="PETR4",
            company_name="PETROBRAS",
            price=Decimal("38.50"),
            change_percent=Decimal("0.043"),
            volume=Decimal("1200000000"),
        )
    ],
)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {WEB_TOKEN}"}


@pytest.fixture
def portal(client: TestClient) -> Iterator[TestClient]:
    async def fake_session() -> Any:
        return None

    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_session] = fake_session
    yield client
    app.dependency_overrides.clear()


def _stub(monkeypatch: pytest.MonkeyPatch, module: Any, name: str, value: Any) -> None:
    async def fake(*_args: object, **_kwargs: object) -> Any:
        return value

    monkeypatch.setattr(module, name, fake)


# --- faixa do header --------------------------------------------------------


def test_faixa_trava_indice_e_cripto_mas_nao_o_bcb(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-017 é por origem: a Selic do BCB é dado aberto e sai sempre."""
    _stub(monkeypatch, market_data, "strip", FAIXA)
    itens = {i["key"]: i for i in portal.get("/v1/market/strip", headers=_headers()).json()}

    assert itens["ibovespa"]["value"] is None
    assert itens["ibovespa"]["missing_reasons"]["value"] == PRICE_REASON
    assert itens["bitcoin"]["value"] is None
    assert itens["bitcoin"]["missing_reasons"]["value"] == CRYPTO_REASON
    assert itens["selic_meta"]["value"] == "10.5", "dado aberto do BCB não depende de licença"


def test_faixa_traz_fonte_em_cada_item(portal: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, market_data, "strip", FAIXA)
    for item in portal.get("/v1/market/strip", headers=_headers()).json():
        assert item["source"]["attribution"]


# --- listas do dia ----------------------------------------------------------


def test_lista_do_dia_declara_metrica_e_piso_de_liquidez(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem os dois, "maiores altas" vira ranking editorial (ADR-018)."""
    _stub(monkeypatch, market_data, "movers", ALTAS)
    corpo = portal.get("/v1/market/movers", headers=_headers()).json()

    assert corpo["metric"] == "change"
    assert corpo["direction"] == "desc"
    assert Decimal(corpo["min_volume"]) == market_data.MIN_VOLUME_DEFAULT


def test_piso_de_liquidez_tem_padrao() -> None:
    """Sem piso, a maior alta é sempre um papel de R$ 3 mil que subiu com um lote."""
    assert market_data.MIN_VOLUME_DEFAULT > 0


def test_metrica_fora_da_lista_fechada_e_422(portal: TestClient) -> None:
    resposta = portal.get("/v1/market/movers", params={"metric": "potencial"}, headers=_headers())
    assert resposta.status_code == 422


def test_metricas_aceitas_sao_factuais() -> None:
    assert set(market_data.MOVER_METRICS) == {"change", "volume"}


def test_movers_respeita_a_trava_de_preco(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(monkeypatch, market_data, "movers", ALTAS)
    item = portal.get("/v1/market/movers", headers=_headers()).json()["items"][0]
    assert item["price"] is None
    assert item["ticker"] == "PETR4", "o papel continua na lista; o preço é que não sai"


# --- contadores e agenda ----------------------------------------------------


def test_contadores_sao_numeros_puros(portal: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, market_data, "strip", FAIXA)
    _stub(monkeypatch, market_data, "movers", ALTAS)
    _stub(monkeypatch, market_data, "counters", {"stock": 412, "fii": 210, "sectors": 33})
    _stub(monkeypatch, repository, "events", [])

    corpo = portal.get("/v1/market/overview", headers=_headers()).json()
    assert corpo["counters"] == {"stock": 412, "fii": 210, "sectors": 33}
    assert all(isinstance(v, int) for v in corpo["counters"].values())


def test_agenda_devolve_fato_com_data_e_fonte(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(
        monkeypatch,
        repository,
        "events",
        [
            schemas.MarketEvent(
                id="ca:42:ex",
                kind="ex_date",
                date=dt.date(2026, 11, 12),
                ticker="PETR4",
                title="PETR4 — Dividendo (data-com)",
                source="b3",
            )
        ],
    )
    evento = portal.get("/v1/market/events", headers=_headers()).json()[0]
    assert evento["date"] == "2026-11-12"
    assert evento["source"] == "b3"


# --- índices ----------------------------------------------------------------


def test_carteira_de_indice_sai_com_a_data(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "Carteira de 02/09/2026", não "composição do Ibovespa": a data é parte do dado."""
    _stub(
        monkeypatch,
        market_data,
        "index_composition",
        schemas.IndexCompositionResult(
            source=FONTE_B3,
            slug="ibovespa",
            reference_date=dt.date(2026, 9, 2),
            members=[schemas.IndexMember(ticker="PETR4", weight=Decimal("0.08124"))],
        ),
    )
    corpo = portal.get("/v1/indices/ibovespa/composition", headers=_headers()).json()
    assert corpo["reference_date"] == "2026-09-02"
    assert corpo["members"][0]["weight"] == "0.08124"


def test_indice_sem_carteira_e_404(portal: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, market_data, "index_composition", None)
    resposta = portal.get("/v1/indices/ibovespa/composition", headers=_headers())
    assert resposta.status_code == 404


# --- Tesouro e cripto -------------------------------------------------------


def test_tesouro_nao_passa_pela_trava_da_b3(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ODbL: `/tesouro` é a única página de preço que sai sem a licença (ADR-017)."""
    _stub(
        monkeypatch,
        market_data,
        "treasury",
        [
            schemas.TreasuryBondItem(
                source=FONTE_TESOURO,
                slug="ipca-2029-05-15",
                name="Tesouro IPCA+ 2029",
                index_type="ipca",
                maturity=dt.date(2029, 5, 15),
                coupon=False,
                date=dt.date(2026, 9, 18),
                buy_rate=Decimal("6.12"),
                buy_price=Decimal("2850.45"),
            )
        ],
    )
    titulo = portal.get("/v1/treasury", headers=_headers()).json()[0]
    assert titulo["buy_price"] == "2850.45"
    assert titulo["source"]["attribution"] == "Fonte: Tesouro Nacional"


def test_cripto_usa_a_trava_propria(portal: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(
        monkeypatch,
        market_data,
        "crypto_list",
        [
            schemas.CryptoItem(
                source=FONTE_CG,
                id="bitcoin",
                symbol="BTC",
                name="Bitcoin",
                price=Decimal("350000"),
            )
        ],
    )
    item = portal.get("/v1/crypto", headers=_headers()).json()[0]
    assert item["price"] is None
    assert item["missing_reasons"]["price"] == CRYPTO_REASON
    assert item["name"] == "Bitcoin", "o ativo continua listado, com '—' no preço"


# --- cotações ---------------------------------------------------------------


def test_papel_desconhecido_volta_na_lista_com_motivo(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O app precisa saber que perguntou por um papel que não temos — sumir seria pior."""
    _stub(
        monkeypatch,
        market_data,
        "quotes",
        [
            schemas.QuoteItem(
                source=FONTE_B3,
                ticker="XXXX9",
                missing_reasons={"price": "papel sem cotação carregada"},
            )
        ],
    )
    item = portal.get("/v1/quotes", params={"symbols": "XXXX9"}, headers=_headers()).json()[0]
    assert item["ticker"] == "XXXX9"
    assert item["price"] is None
    assert item["missing_reasons"]["price"]


# --- trava liberada ---------------------------------------------------------


def test_com_licenca_o_preco_sai() -> None:
    liberado = Gate(Settings(market_b3_prices_enabled=True, market_crypto_enabled=True))
    assert liberado.apply(FAIXA[0]).value == Decimal("142500")
    assert liberado.apply(FAIXA[2], crypto=True).value == Decimal("350000")
