"""Cadastro de papéis da B3 (`sources/b3_listing.py`).

O cadastro anterior lia o ticker de um endpoint que lista **emissores** (`PETR`, não
`PETR4`) e classificava tudo como BDR. Estes testes usam trechos reais dos três arquivos
da B3 (baixados em 23/09/2026) e prendem o que importa: a classe vem da categoria da B3,
não do final do ticker; setor, subsetor e segmento saem da planilha mesclada; e o CNPJ do
emissor não vai parar num fundo.
"""

from __future__ import annotations

import io
from datetime import date

import httpx
import pytest

from alpherion.data.sources import b3_listing
from alpherion.data.sources.b3_api import B3UnavailableError
from alpherion.data.sources.http import check_host

HEADER = (
    "RptDt;TckrSymb;Asst;AsstDesc;SgmtNm;MktNm;SctyCtgyNm;XprtnDt;ISIN;SpcfctnCd;CrpnNm;"
    "CorpGovnLvlNm"
)

LINHAS = [
    "2026-09-22;PETR4;PETR;PETR;CASH;EQUITY-CASH;SHARES;;BRPETRACNPR6;PN      N2;"
    "PETROLEO BRASILEIRO S.A. PETROBRAS;NIVEL 2",
    "2026-09-22;PETR4F;PETR;PETR;ODD LOT;EQUITY-CASH;SHARES;;BRPETRACNPR6;PN;"
    "PETROLEO BRASILEIRO S.A. PETROBRAS;NIVEL 2",
    "2026-09-22;SANB11;SANB;SANB;CASH;EQUITY-CASH;UNIT;;BRSANBCDAM13;UNT;"
    "BCO SANTANDER (BRASIL) S.A.;",
    "2026-09-22;BOVA11;BOVA;ISHARES BOVACI;CASH;EQUITY-CASH;ETF EQUITIES;;BRBOVACTF003;CI;"
    "ISHARES IBOVESPA FUNDO DE ÍNDICE;",
    "2026-09-22;IVVB11;IVVB;IVVB;CASH;EQUITY-CASH;ETF FOREIGN INDEX;;BRIVVBCTF001;CI;"
    "ISHARES S&P 500 FUNDO DE ÍNDICE;",
    "2026-09-22;MXRF11;MXRF;MXRF;CASH;EQUITY-CASH;FUNDS;;BRMXRFCTF008;CI;"
    "MAXI RENDA FDO INV IMOB RESP LIM;",
    "2026-09-22;KNCA11;KNCA;KNCA;CASH;EQUITY-CASH;FUNDS;;BRKNCACTF006;CI;"
    "KINEA CRÉDITO AGRO FIAGRO RESP LIM;",
    "2026-09-22;KDIF11;KDIF;KDIF;CASH;EQUITY-CASH;FUNDS;;BRKDIFCTF009;CI;"
    "KINEA INFRA FIC FI-INFRA RESP LIM;",
    "2026-09-22;AAPL34;AAPL;AAPL;CASH;EQUITY-CASH;BDR;;BRAAPLBDR004;DRN;APPLE INC.;",
    "2026-09-22;PETR10;PETR;PETR;CASH;EQUITY-CASH;RECEIPTS;;BRPETRR01M11;REC;PETROBRAS;",
    "2026-09-22;PETRA400;PETR;PETR;EQUITY CALL;EQUITY-DERIVATE;OPTION ON EQUITIES;;X;;PETROBRAS;",
]


def _arquivo(status: str = "Final") -> str:
    return "\n".join([f"Status do Arquivo: {status}", HEADER, *LINHAS]) + "\n"


def _instrumentos() -> list[b3_listing.Instrument]:
    status, instruments = b3_listing.parse_instruments(io.StringIO(_arquivo()))
    assert status == "Final"
    return instruments


# Planilha da classificação setorial: setor e subsetor mesclados, cabeçalho repetido na
# quebra de página, e "Serviços Diversos" como segmento de dois subsetores diferentes.
PLANILHA = [
    (None, None, None, None, None, None, None),
    (None, "SETOR", "SUBSETOR", "SEGMENTO", "EMISSOR", "", ""),
    (None, "", "", "", "NOME DE PREGÃO", "CÓDIGO", "SEGMENTO DE NEGOCIAÇÃO"),
    (
        None,
        "Petróleo, Gás e Biocombustíveis",
        "Petróleo, Gás e Biocombustíveis",
        "Exploração, Refino e Distribuição",
        "BRAVA",
        "BRAV",
        "Novo Mercado",
    ),
    (None, "", "", "", "PETROBRAS", "PETR", "Nível 2"),
    (None, "SETOR ECONÔMICO", "SUBSETOR", "SEGMENTO", "NOME DE PREGÃO", "CÓDIGO", "SEG"),
    (None, "", "", "", "PRIO", "PRIO", "Novo Mercado"),
    (None, "Financeiro", "Intermediários Financeiros", "Bancos", "SANTANDER", "SANB", "Trad."),
    (None, "", "Serviços Financeiros Diversos", "Serviços Diversos", "B3", "B3SA", "Novo Mercado"),
    (None, "Bens Industriais", "Serviços", "Serviços Diversos", "ATMASA", "ATMP", "Novo Mercado"),
]

EMISSORES = {
    "PETR": b3_listing.Issuer(
        code="PETR",
        company_name="PETRÓLEO BRASILEIRO S.A. - PETROBRAS",
        trade_name="PETROBRAS",
        cnpj="33000167000101",
        cvm_code=9512,
    ),
    # A gestora do ETF é emissora listada; o CNPJ dela não é o do fundo.
    "BOVA": b3_listing.Issuer(
        code="BOVA", company_name="GESTORA", trade_name=None, cnpj="11111111000111", cvm_code=1
    ),
}


# --- instrumentos -----------------------------------------------------------


def test_so_entra_o_lote_padrao_do_mercado_a_vista() -> None:
    tickers = [i.ticker for i in _instrumentos()]
    assert "PETR4" in tickers
    assert "PETR4F" not in tickers, "fracionário é o mesmo papel com outro código"
    assert "PETRA400" not in tickers, "opção não é papel do cadastro"


@pytest.mark.parametrize(
    ("ticker", "esperado"),
    [
        ("PETR4", "stock"),
        ("SANB11", "unit"),
        ("BOVA11", "etf"),
        ("IVVB11", "etf"),
        ("MXRF11", "fii"),
        ("KNCA11", "fiagro"),
        ("AAPL34", "bdr"),
        ("KDIF11", None),  # FI-Infra: sem página, fica de fora
        ("PETR10", None),  # recibo de subscrição
    ],
)
def test_classe_vem_da_categoria_da_b3(ticker: str, esperado: str | None) -> None:
    """O `11` é unit, ETF e FII ao mesmo tempo — só a categoria da B3 desempata."""
    (instrument,) = [i for i in _instrumentos() if i.ticker == ticker]
    assert b3_listing.type_of(instrument) == esperado


def test_status_do_arquivo_e_lido() -> None:
    status, _ = b3_listing.parse_instruments(io.StringIO(_arquivo("Parcial")))
    assert status == "Parcial"


# --- classificação setorial -------------------------------------------------


def test_setor_mesclado_e_herdado_e_cabecalho_repetido_e_pulado() -> None:
    classes = b3_listing.parse_classification(PLANILHA)
    assert set(classes) == {"BRAV", "PETR", "PRIO", "SANB", "B3SA", "ATMP"}
    prio = classes["PRIO"]
    assert prio.sector == "Petróleo, Gás e Biocombustíveis"
    assert prio.segment == "Exploração, Refino e Distribuição"
    assert classes["PETR"].listing_segment == "Nível 2"
    assert classes["B3SA"].sector == "Financeiro", "subsetor novo herda o setor de cima"


def test_slug_curto_e_so_desambiguado_quando_o_segmento_se_repete() -> None:
    slugs = b3_listing.segment_slugs(b3_listing.parse_classification(PLANILHA).values())
    assert slugs[("Intermediários Financeiros", "Bancos")] == "bancos"
    assert slugs[("Petróleo, Gás e Biocombustíveis", "Exploração, Refino e Distribuição")] == (
        "exploracao-refino-e-distribuicao"
    )
    assert slugs[("Serviços Financeiros Diversos", "Serviços Diversos")] == (
        "servicos-financeiros-diversos-servicos-diversos"
    )
    assert slugs[("Serviços", "Serviços Diversos")] == "servicos-servicos-diversos"


def test_slug_sem_acento_e_sem_pontuacao() -> None:
    assert b3_listing.slugify("Petróleo, Gás e Biocombustíveis") == "petroleo-gas-e-biocombustiveis"
    assert b3_listing.slugify(None, "  ") is None


# --- emissores e montagem ---------------------------------------------------


def test_emissor_do_endpoint_de_companhias() -> None:
    registro = {
        "codeCVM": "9512",
        "issuingCompany": "PETR",
        "companyName": "PETRÓLEO BRASILEIRO S.A. - PETROBRAS",
        "tradingName": "PETROBRAS",
        "cnpj": "33000167000101",
    }
    emissor = b3_listing.parse_issuer(registro)
    assert emissor is not None
    assert emissor.cvm_code == 9512
    assert b3_listing.parse_issuer({"companyName": "SEM CÓDIGO"}) is None


def test_listagem_junta_as_tres_fontes() -> None:
    papeis = {
        p.ticker: p
        for p in b3_listing.build_listing(
            _instrumentos(), b3_listing.parse_classification(PLANILHA), EMISSORES
        )
    }
    assert set(papeis) == {"PETR4", "SANB11", "BOVA11", "IVVB11", "MXRF11", "KNCA11", "AAPL34"}

    petr = papeis["PETR4"]
    assert (petr.type, petr.cvm_code, petr.cnpj) == ("stock", 9512, "33000167000101")
    assert petr.sector_slug == "exploracao-refino-e-distribuicao"
    assert petr.isin == "BRPETRACNPR6"
    assert petr.trade_name == "PETROBRAS"

    assert papeis["SANB11"].sector_slug == "bancos"
    assert papeis["BOVA11"].cnpj is None, "o CNPJ da gestora não é o do fundo"
    assert papeis["MXRF11"].sector_slug is None, "segmento de FII vem do informe da CVM"
    assert papeis["MXRF11"].company_name == "MAXI RENDA FDO INV IMOB RESP LIM"


def test_sem_planilha_e_sem_emissores_os_papeis_entram_assim_mesmo() -> None:
    papeis = list(b3_listing.build_listing(_instrumentos(), {}, {}))
    assert len(papeis) == 7
    assert all(p.sector_slug is None and p.cnpj is None for p in papeis)


# --- download ---------------------------------------------------------------


def test_hosts_das_tres_fontes_estao_na_lista() -> None:
    check_host(b3_listing.instruments_request_url(date(2026, 9, 22)))
    check_host(f"{b3_listing.ARQUIVOS_BASE}/?token=x")


def test_recua_ate_o_ultimo_arquivo_final() -> None:
    """Dia sem pregão responde 400; o arquivo do dia corrente pode vir parcial."""
    pedidos: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        pedidos.append(url)
        if "requestname" in url:
            dia = request.url.params["date"]
            if dia == "2026-09-21":  # segunda-feira de feriado fictício
                return httpx.Response(400, json={"title": "Bad Request"})
            return httpx.Response(200, json={"redirectUrl": f"~/download?token={dia}"})
        token = request.url.params["token"]
        status = "Parcial" if token == "2026-09-23" else "Final"
        # O arquivo real é latin-1, não UTF-8.
        return httpx.Response(200, content=_arquivo(status).encode("latin-1"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        dia, instrumentos = b3_listing.fetch_instruments(date(2026, 9, 23), http=http)

    assert dia == date(2026, 9, 22), "o parcial de hoje perde para o final de ontem"
    assert len(instrumentos) == 9
    knca = next(i for i in instrumentos if i.ticker == "KNCA11")
    assert knca.name == "KINEA CRÉDITO AGRO FIAGRO RESP LIM"


def test_sem_nenhum_arquivo_na_janela_e_falha_explicita() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"title": "Bad Request"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as http,
        pytest.raises(B3UnavailableError, match="nenhum cadastro"),
    ):
        b3_listing.fetch_instruments(date(2026, 9, 23), http=http)
