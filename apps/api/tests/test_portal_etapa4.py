"""O que a Etapa 4 (portal) acrescentou à API.

- **Faixa:** o header recebe só os cinco itens dele; CDI e IPCA saem como acumulado
  **composto** em 12 meses, e janela incompleta vira `null` com motivo, nunca número.
- **Busca global:** agrupada por classe, com a trava do ADR-017 por origem.
- **Agenda:** vários tipos por consulta, janela limitada, e a classe do papel no evento
  para o filtro da página.
- **Setor:** agregado é soma e contagem; o valor de mercado passa pela trava.
- **Revalidação:** as semanas da agenda no mesmo formato que o `web` usa.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from decimal import Decimal
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alpherion.data import scheduler
from alpherion.data.jobs.revalidate_pages import agenda_paths
from alpherion.db.session import get_session
from alpherion.market import accumulated, market_data, repository, schemas
from alpherion.market.flags import PRICE_REASON

from .conftest import WEB_TOKEN

FONTE_B3 = schemas.SourceRef(source="b3", attribution="Fonte: B3")


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


# --- acumulado em 12 meses --------------------------------------------------


def _mensal(
    valores: list[str], fim: dt.date = dt.date(2026, 8, 1)
) -> list[tuple[dt.date, Decimal]]:
    pontos: list[tuple[dt.date, Decimal]] = []
    ano, mes = fim.year, fim.month
    for valor in reversed(valores):
        pontos.append((dt.date(ano, mes, 1), Decimal(valor)))
        ano, mes = (ano, mes - 1) if mes > 1 else (ano - 1, 12)
    return list(reversed(pontos))


def test_ipca_12m_e_composto_nao_somado() -> None:
    """12 meses de 0,9% são 11,35%, não 10,8%."""
    resultado = accumulated.monthly_12m(_mensal(["0.9"] * 12))
    assert resultado.value == Decimal("11.35")
    assert resultado.as_of == dt.date(2026, 8, 1)
    assert resultado.reason is None


def test_ipca_12m_usa_so_os_ultimos_doze_meses() -> None:
    resultado = accumulated.monthly_12m(_mensal(["5.0"] * 3 + ["0.5"] * 12))
    assert resultado.value == Decimal("6.17")


def test_ipca_com_mes_faltando_nao_vira_numero() -> None:
    pontos = _mensal(["0.4"] * 13)
    del pontos[5]
    resultado = accumulated.monthly_12m(pontos)
    assert resultado.value is None
    assert resultado.reason == "série sem os 12 meses completos"


def test_ipca_com_menos_de_doze_meses_nao_vira_numero() -> None:
    assert accumulated.monthly_12m(_mensal(["0.4"] * 7)).value is None


def test_cdi_12m_compoe_a_taxa_diaria() -> None:
    """252 dias úteis de 0,04% a.d. = 1,0004²⁵² − 1 ≈ 10,60% no ano."""
    fim = dt.date(2026, 9, 22)
    pontos: list[tuple[dt.date, Decimal]] = []
    dia = fim - dt.timedelta(days=364)
    while len(pontos) < 252:
        if dia.weekday() < 5:
            pontos.append((dia, Decimal("0.04")))
        dia += dt.timedelta(days=1)
    pontos[-1] = (fim, Decimal("0.04"))
    resultado = accumulated.daily_12m(pontos)
    assert resultado.value == Decimal("10.60")
    assert resultado.as_of == fim


def test_cdi_com_serie_curta_nao_vira_numero() -> None:
    fim = dt.date(2026, 9, 22)
    pontos = [(fim - dt.timedelta(days=d), Decimal("0.04")) for d in range(0, 200)]
    resultado = accumulated.daily_12m(pontos)
    assert resultado.value is None
    assert resultado.reason == "série com menos de 12 meses carregados"


def test_serie_vazia_diz_que_nao_carregou() -> None:
    assert accumulated.daily_12m([]).reason == "série ainda não carregada"
    assert accumulated.monthly_12m([]).reason == "série ainda não carregada"


# --- faixa ------------------------------------------------------------------


def test_header_pede_so_os_cinco_itens_dele(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    pedidos: list[object] = []

    async def fake_strip(_session: object, keys: object = None) -> list[schemas.StripItem]:
        pedidos.append(keys)
        return []

    monkeypatch.setattr(market_data, "strip", fake_strip)
    portal.get("/v1/market/strip", headers=_headers())
    assert pedidos == [market_data.HEADER_STRIP_KEYS]
    assert market_data.HEADER_STRIP_KEYS == ("ibovespa", "ifix", "ptax_venda", "cdi_12m", "bitcoin")


def test_faixa_completa_tem_os_nove_itens_do_portal() -> None:
    chaves = [key for key, _label, _kind in market_data.STRIP_ITEMS]
    assert chaves == [
        "ibovespa",
        "ifix",
        "idiv",
        "smll",
        "ptax_venda",
        "selic_meta",
        "cdi_12m",
        "ipca_12m",
        "bitcoin",
    ]
    assert set(market_data.HEADER_STRIP_KEYS) <= set(chaves)


def test_acumulado_do_bcb_nao_passa_pela_trava(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CDI e IPCA são dado aberto do BCB: saem mesmo sem a licença da B3."""
    item = schemas.StripItem(
        source=schemas.SourceRef(source="bcb", attribution="Fonte: BCB"),
        key="cdi_12m",
        label="CDI 12 m",
        value=Decimal("10.9"),
        unit="%",
    )

    async def fake_strip(_session: object, _keys: object = None) -> list[schemas.StripItem]:
        return [item]

    monkeypatch.setattr(market_data, "strip", fake_strip)
    (corpo,) = portal.get("/v1/market/strip", headers=_headers()).json()
    assert corpo["value"] == "10.9"


# --- busca global -----------------------------------------------------------


def _busca() -> schemas.AssetSearchResult:
    return schemas.AssetSearchResult(
        query="petr",
        groups=[
            schemas.AssetSearchGroup(
                asset_class="stock",
                items=[
                    schemas.AssetHit(
                        type="stock", code="PETR4", name="Petrobras", price=Decimal("38.5")
                    )
                ],
            ),
            schemas.AssetSearchGroup(
                asset_class="crypto",
                items=[
                    schemas.AssetHit(
                        type="crypto", code="bitcoin", name="Bitcoin (BTC)", price=Decimal("1")
                    )
                ],
            ),
        ],
    )


def test_busca_sai_agrupada_e_com_a_trava_por_origem(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(*_args: object, **_kwargs: object) -> schemas.AssetSearchResult:
        return _busca()

    monkeypatch.setattr(market_data, "search_assets", fake)
    corpo = portal.get("/v1/assets/search", params={"q": "petr"}, headers=_headers()).json()

    assert [g["asset_class"] for g in corpo["groups"]] == ["stock", "crypto"]
    acao = corpo["groups"][0]["items"][0]
    cripto = corpo["groups"][1]["items"][0]
    assert acao["code"] == "PETR4" and acao["price"] is None
    assert acao["missing_reasons"]["price"] == PRICE_REASON
    assert cripto["price"] is None, "cripto tem trava própria, e ela vale na busca também"


def test_ordem_dos_grupos_e_fixa() -> None:
    assert market_data.ASSET_CLASSES == (
        "stock",
        "fii",
        "etf",
        "bdr",
        "index",
        "treasury",
        "crypto",
    )


def test_busca_limite_e_por_grupo(portal: TestClient) -> None:
    resposta = portal.get("/v1/assets/search", params={"q": "pe", "limit": 50}, headers=_headers())
    assert resposta.status_code == 422


# --- agenda -----------------------------------------------------------------


def test_agenda_aceita_varios_tipos_e_a_classe(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    recebido: dict[str, Any] = {}

    async def fake(_session: object, **kwargs: Any) -> list[schemas.MarketEvent]:
        recebido.update(kwargs)
        return [
            schemas.MarketEvent(
                id="ca:1:ex",
                kind="ex_date",
                date=dt.date(2026, 9, 24),
                ticker="MXRF11",
                security_type="fii",
                title="MXRF11 — Rendimento (data-com)",
                source="b3",
            )
        ]

    monkeypatch.setattr(repository, "events", fake)
    corpo = portal.get(
        "/v1/market/events",
        params=[
            ("from", "2026-09-21"),
            ("to", "2026-09-27"),
            ("kind", "ex_date"),
            ("kind", "payment"),
            ("type", "fii"),
            ("category", "Fato Relevante"),
        ],
        headers=_headers(),
    ).json()

    assert recebido["kind"] == ["ex_date", "payment"]
    assert recebido["type_"] == "fii"
    assert recebido["document_categories"] == ["Fato Relevante"]
    assert corpo[0]["security_type"] == "fii"


def test_agenda_recusa_janela_longa(portal: TestClient) -> None:
    resposta = portal.get(
        "/v1/market/events",
        params={"from": "2026-01-01", "to": "2026-06-30"},
        headers=_headers(),
    )
    assert resposta.status_code == 422


def test_agenda_recusa_janela_invertida(portal: TestClient) -> None:
    resposta = portal.get(
        "/v1/market/events",
        params={"from": "2026-09-30", "to": "2026-09-01"},
        headers=_headers(),
    )
    assert resposta.status_code == 422


def test_tipo_de_evento_fora_da_lista_e_422(portal: TestClient) -> None:
    resposta = portal.get("/v1/market/events", params={"kind": "palpite"}, headers=_headers())
    assert resposta.status_code == 422


def test_teto_da_agenda_e_quinhentos(portal: TestClient) -> None:
    assert repository.MAX_EVENTS == 500
    resposta = portal.get("/v1/market/events", params={"limit": 501}, headers=_headers())
    assert resposta.status_code == 422


def test_contagem_mensal_da_agenda(portal: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(_session: object, **_kwargs: Any) -> list[schemas.EventCount]:
        return [schemas.EventCount(date=dt.date(2026, 10, 1), kind="payment", count=37)]

    monkeypatch.setattr(repository, "event_counts", fake)
    corpo = portal.get(
        "/v1/market/events/calendar",
        params={"from": "2026-09-28", "to": "2026-11-01"},
        headers=_headers(),
    ).json()
    assert corpo == [{"date": "2026-10-01", "kind": "payment", "count": 37}]


# --- setor ------------------------------------------------------------------


def test_setor_soma_valor_de_mercado_atras_da_trava(
    portal: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake(*_args: object, **_kwargs: object) -> schemas.SectorDetail:
        return schemas.SectorDetail(
            source=FONTE_B3,
            slug="bancos",
            name="Bancos",
            kind="b3_segment",
            sector="Financeiro",
            subsector="Intermediários financeiros",
            securities_count=23,
            market_cap=Decimal("1200000000000"),
            market_cap_count=20,
        )

    monkeypatch.setattr(market_data, "sector", fake)
    corpo = portal.get("/v1/sectors/bancos", headers=_headers()).json()
    assert corpo["securities_count"] == 23
    assert corpo["market_cap"] is None
    assert corpo["missing_reasons"]["market_cap"] == PRICE_REASON


def test_linha_de_lista_trava_os_multiplos_de_preco() -> None:
    """P/L, P/VP, DY e valor de mercado dependem do preço; ROE não."""
    from alpherion.market.flags import Gate
    from alpherion.settings import Settings

    linha = schemas.SecuritySummary(
        ticker="ITUB4",
        type="stock",
        company_name="ITAU UNIBANCO",
        price=Decimal("35"),
        pe=Decimal("9"),
        pvp=Decimal("1.8"),
        dy_12m=Decimal("0.07"),
        roe=Decimal("0.21"),
        market_cap=Decimal("340000000000"),
    )
    travada = Gate(Settings(market_b3_prices_enabled=False)).apply(linha)
    assert travada.pe is None and travada.pvp is None and travada.dy_12m is None
    assert travada.market_cap is None
    assert travada.missing_reasons["pe"] == PRICE_REASON
    assert travada.roe == Decimal("0.21")


def test_classe_pedida_traz_unit_e_fiagro() -> None:
    assert repository.TYPE_FAMILIES["stock"] == ("stock", "unit")
    assert repository.TYPE_FAMILIES["fii"] == ("fii", "fiagro")


# --- revalidação ------------------------------------------------------------


def test_revalidacao_cobre_as_semanas_da_agenda_no_formato_do_web() -> None:
    assert agenda_paths(dt.date(2026, 9, 23)) == [
        "/agenda/2026-39",
        "/agenda/2026-40",
        "/agenda/mes/2026-09",
    ]


def test_virada_de_ano_usa_o_ano_iso() -> None:
    """31/12/2026 cai na semana 53 de 2026; 07/01/2027 na semana 1 de 2027."""
    assert agenda_paths(dt.date(2026, 12, 31))[:2] == ["/agenda/2026-53", "/agenda/2027-01"]


def test_agenda_e_reconstruida_antes_da_revalidacao() -> None:
    horas = {entry.name: (entry.hour, entry.minute) for entry in scheduler.SCHEDULE}
    assert horas["market_events_rebuild"] < horas["revalidate_pages"]


def test_papel_sem_negocio_diz_por_que_e_a_trava_nao_apaga() -> None:
    from alpherion.db.models import Security
    from alpherion.market.flags import Gate
    from alpherion.settings import Settings

    linha = repository._summary(
        Security(ticker="ABCB4", type="stock", company_name="ABC BRASIL", status="active")
    )
    assert linha.price is None
    assert linha.missing_reasons["price"] == repository.NO_TRADE_REASON
    travada = Gate(Settings(market_b3_prices_enabled=False)).apply(linha)
    assert travada.missing_reasons["price"] == repository.NO_TRADE_REASON
