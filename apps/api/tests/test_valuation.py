"""Valorização da carteira (`market/valuation.py`) e a trava do ADR-017 sobre ela."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from alpherion.db.session import get_session
from alpherion.market import valuation
from alpherion.market.flags import CRYPTO_REASON, PRICE_REASON, Gate
from alpherion.settings import Settings

from .conftest import IMPORTS_TOKEN, WEB_TOKEN

HOJE = date(2026, 9, 18)


class FakePrices:
    def __init__(self) -> None:
        self.asked: dict[str, set[str]] = {}

    async def quotes(self, tickers: set[str]) -> Mapping[str, valuation.Quote]:
        self.asked["quotes"] = tickers
        return {"PETR4": valuation.Quote(Decimal("40"), HOJE)} if "PETR4" in tickers else {}

    async def crypto(self, ids: set[str]) -> Mapping[str, valuation.Quote]:
        self.asked["crypto"] = ids
        return {"bitcoin": valuation.Quote(Decimal("350000"), HOJE)} if "bitcoin" in ids else {}

    async def treasury(self, slugs: set[str]) -> Mapping[str, valuation.Quote]:
        self.asked["treasury"] = slugs
        return {"ipca-2035-05-15": valuation.Quote(Decimal("2200"), date(2026, 9, 17))}


def _request() -> valuation.ValuationRequest:
    return valuation.ValuationRequest.model_validate(
        {
            "positions": [
                {
                    "symbol": "PETR4",
                    "market_ref": "ticker",
                    "asset_class": "stock_br",
                    "quantity": "100",
                    "avg_price": "30",
                },
                {
                    "symbol": "ipca-2035-05-15",
                    "market_ref": "treasury_slug",
                    "asset_class": "treasury",
                    "quantity": "1.5",
                    "avg_price": "2000",
                },
                {
                    "symbol": "bitcoin",
                    "market_ref": "coingecko_id",
                    "asset_class": "crypto",
                    "quantity": "0.01",
                },
                {
                    "symbol": "CDB924",
                    "market_ref": "none",
                    "asset_class": "fixed_income",
                    "value_brl": "5490",
                },
            ]
        }
    )


def _run(gate: Gate) -> tuple[valuation.Valuation, FakePrices]:
    prices = FakePrices()
    return asyncio.run(valuation.value_positions(_request(), prices, gate)), prices


def test_tudo_liberado() -> None:
    result, _ = _run(Gate(Settings(market_b3_prices_enabled=True, market_crypto_enabled=True)))
    petr, ipca, btc, cdb = result.positions
    assert (petr.value, petr.cost, petr.result, petr.result_percent) == (
        Decimal("4000.00"),
        Decimal("3000.00"),
        Decimal("1000.00"),
        Decimal("0.333333"),
    )
    assert (ipca.value, ipca.result, ipca.source) == (
        Decimal("3300.00"),
        Decimal("300.00"),
        "Fonte: Tesouro Transparente",
    )
    assert btc.value == Decimal("3500.00") and btc.cost is None and "cost" in btc.missing_reasons
    assert cdb.value == Decimal("5490.00") and cdb.source is None
    assert result.total_value == Decimal("16290.00")
    assert sum(p.weight or 0 for p in result.positions) == pytest.approx(
        Decimal(1), abs=Decimal("0.00001")
    )
    # Resultado total só do que tem custo e valor (PETR4 e o título).
    assert (result.total_cost, result.total_result) == (Decimal("6000.00"), Decimal("1300.00"))
    assert result.partial is True
    assert result.as_of == HOJE


def test_sem_licenca_preco_sai_nulo_com_motivo_e_nem_e_consultado() -> None:
    result, prices = _run(
        Gate(Settings(market_b3_prices_enabled=False, market_crypto_enabled=False))
    )
    petr, ipca, btc, _ = result.positions
    assert petr.price is None and petr.value is None and petr.weight is None
    assert petr.missing_reasons["price"] == PRICE_REASON
    assert btc.missing_reasons["price"] == CRYPTO_REASON
    assert prices.asked["quotes"] == set() and prices.asked["crypto"] == set()
    # Tesouro Transparente é dado público: não passa pela trava.
    assert ipca.value == Decimal("3300.00")
    assert result.total_value == Decimal("8790.00")
    assert result.partial is True


def test_sem_preco_recente() -> None:
    request = valuation.ValuationRequest.model_validate(
        {
            "positions": [
                {
                    "symbol": "XPTO3",
                    "market_ref": "ticker",
                    "asset_class": "stock_br",
                    "quantity": "1",
                }
            ]
        }
    )
    gate = Gate(Settings(market_b3_prices_enabled=True))
    result = asyncio.run(valuation.value_positions(request, FakePrices(), gate))
    assert "45 dias" in result.positions[0].missing_reasons["price"]
    assert result.total_value == 0 and result.total_result is None


def test_quantidade_ou_valor() -> None:
    with pytest.raises(ValueError, match="um dos dois"):
        valuation.ValuationPosition.model_validate(
            {
                "symbol": "X",
                "market_ref": "none",
                "asset_class": "other",
                "quantity": "1",
                "value_brl": "1",
            }
        )


@pytest.fixture
def valuation_client(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    async def fake_session() -> Any:
        yield None

    app = client.app
    app.dependency_overrides[get_session] = fake_session  # type: ignore[attr-defined]
    monkeypatch.setattr(valuation, "DbPriceSource", lambda _s, _d: FakePrices())
    yield client
    app.dependency_overrides.clear()  # type: ignore[attr-defined]


def test_rota(valuation_client: TestClient) -> None:
    body = _request().model_dump(mode="json")
    response = valuation_client.post(
        "/v1/portfolios/valuation", json=body, headers={"Authorization": f"Bearer {WEB_TOKEN}"}
    )
    assert response.status_code == 200, response.text
    # Sem licença no ambiente de teste: PETR4 sem preço, com o motivo.
    assert response.json()["positions"][0]["missing_reasons"]["price"] == PRICE_REASON

    sem_escopo = valuation_client.post(
        "/v1/portfolios/valuation", json=body, headers={"Authorization": f"Bearer {IMPORTS_TOKEN}"}
    )
    assert sem_escopo.status_code == 403


def test_rota_limite_de_posicoes(valuation_client: TestClient) -> None:
    posicao = {
        "symbol": "PETR4",
        "market_ref": "ticker",
        "asset_class": "stock_br",
        "quantity": "1",
    }
    response = valuation_client.post(
        "/v1/portfolios/valuation",
        json={"positions": [posicao] * 101},
        headers={"Authorization": f"Bearer {WEB_TOKEN}"},
    )
    assert response.status_code == 422
