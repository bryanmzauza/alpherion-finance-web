"""Fontes liberadas para produção: Tesouro Transparente (ODbL) e BCB SGS."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from alpherion.data.sources import bcb, tesouro
from alpherion.data.sources.http import SourceError

# Cabeçalho real do CSV do Tesouro Transparente (nomes por extenso, sem acento).
CABECALHO = (
    "Tipo Titulo;Data Vencimento;Data Base;"
    "Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha"
)
CSV_TESOURO = f"""{CABECALHO}
Tesouro IPCA+ 2029;15/05/2029;21/09/2026;7,25;7,35;3.145,67;3.140,12
Tesouro IPCA+ com Juros Semestrais 2035;15/05/2035;21/09/2026;7,10;7,20;4.012,45;4.008,90
Tesouro Selic 2031;01/03/2031;21/09/2026;0,05;0,11;15.234,56;15.230,00
Tesouro Prefixado 2028;01/01/2028;21/09/2026;12,50;12,60;;
Tesouro Educa+ 2032;15/12/2032;21/09/2026;7,00;7,10;1.234,56;1.230,00
"""


@pytest.fixture
def linhas_tesouro() -> list[str]:
    return CSV_TESOURO.splitlines()


def test_tesouro_le_linhas(linhas_tesouro: list[str]) -> None:
    rows = list(tesouro.parse_csv(iter(linhas_tesouro)))
    assert len(rows) == 5


def test_tesouro_converte_decimal_brasileiro(linhas_tesouro: list[str]) -> None:
    """`3.145,67` é três mil e cento e quarenta e cinco — não 3,14567."""
    ipca = next(r for r in tesouro.parse_csv(iter(linhas_tesouro)) if r.maturity.year == 2029)
    assert ipca.buy_price == Decimal("3145.67")
    assert ipca.buy_rate == Decimal("7.25")
    assert ipca.date == date(2026, 9, 21)


def test_tesouro_campo_vazio_vira_none(linhas_tesouro: list[str]) -> None:
    """Preço ausente é ausência, não zero (§3.5: a página mostra "—")."""
    pre = next(r for r in tesouro.parse_csv(iter(linhas_tesouro)) if r.index_type == "prefixado")
    assert pre.buy_price is None
    assert pre.sell_price is None
    assert pre.buy_rate == Decimal("12.50")


def test_tesouro_detecta_indexador(linhas_tesouro: list[str]) -> None:
    tipos = {r.slug: r.index_type for r in tesouro.parse_csv(iter(linhas_tesouro))}
    assert set(tipos.values()) == {"ipca", "selic", "prefixado", "educa_mais"}


def test_tesouro_slug_separa_titulos_com_juros_semestrais(linhas_tesouro: list[str]) -> None:
    """Dois IPCA+ podem vencer no mesmo mês; o slug precisa distinguir."""
    slugs = {r.slug for r in tesouro.parse_csv(iter(linhas_tesouro))}
    assert "ipca-2029-05-15" in slugs
    assert "ipca-2035-05-15-juros" in slugs


def test_tesouro_marca_cupom(linhas_tesouro: list[str]) -> None:
    com_juros = next(r for r in tesouro.parse_csv(iter(linhas_tesouro)) if r.coupon)
    assert com_juros.maturity == date(2035, 5, 15)
    assert sum(1 for r in tesouro.parse_csv(iter(linhas_tesouro)) if r.coupon) == 1


# --- BCB SGS ---


def _bcb_client(payload: object, status: int = 200) -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        if isinstance(payload, str):
            return httpx.Response(status, text=payload)
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    """As novas tentativas do SGS esperam segundos; nos testes, não."""
    monkeypatch.setattr(bcb, "RETRY_DELAYS", (0.0, 0.0))


def test_bcb_le_serie() -> None:
    client = _bcb_client(
        [{"data": "19/09/2026", "valor": "0.054"}, {"data": "22/09/2026", "valor": "0.055"}]
    )
    points = bcb.fetch("cdi", start=date(2026, 9, 1), end=date(2026, 9, 22), http=client)
    assert [p.date for p in points] == [date(2026, 9, 19), date(2026, 9, 22)]
    assert points[0].value == Decimal("0.054")
    assert points[0].series == "cdi"


def test_bcb_aceita_decimal_com_virgula() -> None:
    points = bcb.fetch("ipca", http=_bcb_client([{"data": "01/09/2026", "valor": "0,45"}]))
    assert points[0].value == Decimal("0.45")


def test_bcb_ignora_ponto_sem_valor() -> None:
    """O SGS publica a data antes do número em alguns índices."""
    points = bcb.fetch("ipca", http=_bcb_client([{"data": "01/10/2026", "valor": ""}]))
    assert points == []


def test_bcb_serie_desconhecida_e_erro() -> None:
    with pytest.raises(SourceError, match="série desconhecida"):
        bcb.fetch("bitcoin")


def test_bcb_html_nao_vira_serie_vazia() -> None:
    """Quando o SGS cai, ele responde HTML com 200 — não pode virar "sem dados"."""
    with pytest.raises(SourceError, match="não é JSON"):
        bcb.fetch("cdi", http=_bcb_client("<html>manutenção</html>"))


def test_bcb_http_de_erro() -> None:
    with pytest.raises(SourceError, match="HTTP 500"):
        bcb.fetch("cdi", http=_bcb_client([], status=500))


@pytest.mark.parametrize(
    ("nome", "esperado"),
    [
        ("Tesouro IGPM+ com Juros Semestrais", "igpm"),
        ("Tesouro IPCA+ com Juros Semestrais", "ipca"),
        ("Tesouro Selic", "selic"),
        ("Tesouro Educa+", "educa_mais"),
        ("Tesouro Qualquer Coisa Nova", "outro"),
    ],
)
def test_indexador_pelo_nome_do_titulo(nome: str, esperado: str) -> None:
    """O IGP-M caía em "selic" porque nome desconhecido virava Selic em silêncio."""
    assert tesouro.detect_index_type(nome) == esperado


def test_serie_diaria_vai_em_janelas_de_ate_dez_anos() -> None:
    """Desde 2025 o SGS responde 406 a série diária sem data ou com mais de 10 anos."""
    pedidos: list[httpx.QueryParams] = []

    def handler(request: httpx.Request) -> httpx.Response:
        pedidos.append(request.url.params)
        return httpx.Response(200, json=[])

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        bcb.fetch("cdi", end=date(2026, 9, 23), http=http)

    assert len(pedidos) == 5  # 1986 → 2026 em janelas de ~10 anos
    assert pedidos[0]["dataInicial"] == "01/01/1986"
    assert pedidos[-1]["dataFinal"] == "23/09/2026"
    for inicio, fim in bcb.windows(date(1986, 1, 1), date(2026, 9, 23)):
        assert fim - inicio <= bcb.MAX_DAILY_WINDOW < timedelta(days=3650)


def test_janela_anterior_ao_inicio_da_serie_nao_e_erro() -> None:
    """O SGS responde 404 antes de a série existir (CDI antes de 1986, PTAX antes de 1984)."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["dataInicial"].endswith("1986"):
            return httpx.Response(404, json={"erro": {"statusCode": 404}})
        return httpx.Response(200, json=[{"data": "02/01/2026", "valor": "0.05"}])

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        points = bcb.fetch("cdi", end=date(2026, 9, 23), http=http)
    assert len(points) == 4


def test_serie_mensal_continua_numa_chamada_so() -> None:
    pedidos: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        pedidos.append(str(request.url))
        return httpx.Response(200, json=[{"data": "01/08/2026", "valor": "0.12"}])

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        bcb.fetch("ipca", http=http)
    assert len(pedidos) == 1
    assert "dataInicial" not in pedidos[0]


def test_pagina_de_erro_passageira_e_tentada_de_novo() -> None:
    """O SGS às vezes devolve HTML numa janela que responde certo segundos depois."""
    tentativas: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        tentativas.append(1)
        if len(tentativas) == 1:
            return httpx.Response(200, text="<html>erro</html>")
        return httpx.Response(200, json=[{"data": "01/08/2026", "valor": "15.00"}])

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        points = bcb.fetch("ipca", http=http)
    assert len(tentativas) == 2
    assert len(points) == 1


def test_codigos_do_sgs_documentados() -> None:
    """Os códigos são o elo com a fonte: se mudarem, o número muda de significado."""
    assert bcb.SERIES["selic"] == 11
    assert bcb.SERIES["cdi"] == 12
    assert bcb.SERIES["ipca"] == 433
    assert bcb.SERIES["ptax_venda"] == 1
