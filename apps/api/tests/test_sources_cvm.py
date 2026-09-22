"""Fontes da CVM: cadastro, informes de FII, FCA e IPE.

Fixtures sintéticas, escritas com o cabeçalho de cada conjunto. O que os testes
protegem não é o nome da coluna (a CVM renomeia; a leitura é por apelido) — é o
significado: ausência vira `None`, versão maior vence, cancelado sai da lista e
documento **nenhum** é baixado.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from alpherion.data.sources import cvm, cvm_documents
from alpherion.data.transform.csv_fields import Row, read_rows


def _csv(tmp_path: Path, name: str, header: str, *lines: str) -> Path:
    path = tmp_path / name
    path.write_text("\n".join([header, *lines]) + "\n", encoding="latin-1")
    return path


def _rows(path: Path) -> list[Row]:
    return list(read_rows(path))


# --- csv_fields -------------------------------------------------------------


def test_coluna_e_achada_por_apelido_e_sem_acento(tmp_path: Path) -> None:
    path = _csv(tmp_path, "a.csv", "Código CVM;Valor", "99999;1.234,56")
    (row,) = _rows(path)
    assert row.integer("cd_cvm", "codigo_cvm") == 99999
    assert row.decimal("valor") == Decimal("1234.56")


def test_campo_vazio_e_marcador_de_ausencia_viram_none(tmp_path: Path) -> None:
    """Zero inventado vira indicador errado na página; ausência tem de ficar ausente."""
    path = _csv(tmp_path, "a.csv", "A;B;C", ";-;Não informado")
    (row,) = _rows(path)
    assert row.decimal("a") is None
    assert row.get("b") is None
    assert row.text("c") is None


def test_cnpj_guarda_so_os_digitos(tmp_path: Path) -> None:
    path = _csv(tmp_path, "a.csv", "CNPJ_Fundo", "12.345.678/0001-90")
    (row,) = _rows(path)
    assert row.digits("cnpj_fundo") == "12345678000190"


def test_data_aceita_os_dois_formatos(tmp_path: Path) -> None:
    path = _csv(tmp_path, "a.csv", "A;B", "2025-03-31;31/03/2025")
    (row,) = _rows(path)
    assert row.date("a") == row.date("b") == date(2025, 3, 31)


# --- cadastro de companhias -------------------------------------------------

CAD_HEADER = "CNPJ_CIA;DENOM_SOCIAL;DENOM_COMERC;DT_REG;CD_CVM;SETOR_ATIV;SIT;SITE"


def test_cadastro_de_companhia(tmp_path: Path) -> None:
    path = _csv(
        tmp_path,
        "cad_cia_aberta.csv",
        CAD_HEADER,
        "00.000.000/0001-91;COMPANHIA DE TESTE SA;TESTE;2010-05-03;99999;"
        "Petróleo e Gás;ATIVO;https://ri.teste.com.br",
        "11.111.111/0001-11;EXTINTA SA;;1998-01-02;88888;Comércio;CANCELADA;",
    )
    ativa, cancelada = list(cvm.parse_companies(read_rows(path)))
    assert (ativa.cvm_code, ativa.cnpj, ativa.status) == (99999, "00000000000191", "active")
    assert ativa.cvm_sector == "Petróleo e Gás"
    assert ativa.ri_url == "https://ri.teste.com.br"
    assert cancelada.status == "inactive"
    assert cancelada.ri_url is None


def test_cadastro_sem_codigo_cvm_e_descartado(tmp_path: Path) -> None:
    """Sem `cvm_code` não há como ligar a companhia às demonstrações."""
    path = _csv(tmp_path, "cad.csv", CAD_HEADER, "00.000.000/0001-91;SEM CODIGO SA;;;;;ATIVO;")
    assert list(cvm.parse_companies(read_rows(path))) == []


# --- informes de FII --------------------------------------------------------

FII_GERAL = "CNPJ_Fundo;Data_Referencia;Versao;Quantidade_Cotistas;Segmento"
FII_COMPL = (
    "CNPJ_Fundo;Data_Referencia;Versao;Patrimonio_Liquido;Valor_Patrimonial_Cotas;"
    "Cotas_Emitidas;Percentual_Despesas_Taxa_Administracao"
)


def test_informe_de_fii_junta_os_arquivos_do_pacote(tmp_path: Path) -> None:
    geral = _csv(tmp_path, "geral.csv", FII_GERAL, "12.345.678/0001-90;2026-08-31;1;150000;Papel")
    compl = _csv(
        tmp_path,
        "complemento.csv",
        FII_COMPL,
        "12.345.678/0001-90;2026-08-31;1;1.200.000.000,00;104,55;11.478.000;0,95",
    )
    rows = [r for path in (geral, compl) for r in cvm.parse_fii_monthly(read_rows(path))]
    (report,) = cvm.merge_fii_reports(iter(rows))

    assert report.period == date(2026, 8, 1), "o informe é mensal: a chave é o 1º do mês"
    assert report.shareholders == 150000
    assert report.segment == "Papel"
    assert report.nav == Decimal("1200000000.00")
    assert report.nav_per_share == Decimal("104.55")
    assert report.admin_fee == Decimal("0.95")


def test_informe_de_fii_republicado_manda_no_que_trouxer(tmp_path: Path) -> None:
    """Versão 2 corrige o PL; o que ela não traz continua vindo da versão 1."""
    v1 = _csv(
        tmp_path,
        "v1.csv",
        FII_COMPL,
        "12.345.678/0001-90;2026-08-31;1;1.200.000.000,00;104,55;11.478.000;0,95",
    )
    v2 = _csv(tmp_path, "v2.csv", FII_COMPL, "12.345.678/0001-90;2026-08-31;2;900.000.000,00;;;")
    rows = [r for path in (v1, v2) for r in cvm.parse_fii_monthly(read_rows(path))]
    (report,) = cvm.merge_fii_reports(iter(rows))

    assert report.version == 2
    assert report.nav == Decimal("900000000.00")
    assert report.nav_per_share == Decimal("104.55")


def test_vacancia_ausente_fica_none(tmp_path: Path) -> None:
    path = _csv(tmp_path, "geral.csv", FII_GERAL, "12.345.678/0001-90;2026-08-31;1;150000;Papel")
    (report,) = list(cvm.parse_fii_monthly(read_rows(path)))
    assert report.vacancy_physical is None
    assert report.vacancy_financial is None


# --- FCA --------------------------------------------------------------------

FCA_HEADER = "Codigo_CVM;Data_Referencia;Versao;Tipo_Capital;Valor_Capital;Quantidade_Total_Acoes"


def test_fca_fica_so_com_o_capital_integralizado(tmp_path: Path) -> None:
    path = _csv(
        tmp_path,
        "capital_social.csv",
        FCA_HEADER,
        "99999;2026-05-31;1;Capital Emitido;10.000.000,00;20.000.000",
        "99999;2026-05-31;1;Capital Integralizado;8.000.000,00;13.044.496.930",
    )
    (fact,) = list(cvm.parse_company_facts(read_rows(path)))
    assert fact.shares_outstanding == Decimal("13044496930")
    assert fact.capital_social == Decimal("8000000.00")


# --- IPE --------------------------------------------------------------------

IPE_HEADER = (
    "CNPJ_Companhia;Nome_Companhia;Codigo_CVM;Categoria;Tipo;Assunto;"
    "Data_Referencia;Data_Entrega;Status;Versao;Protocolo_Entrega;Link_Download"
)
IPE_FATO = (
    "00.000.000/0001-91;COMPANHIA DE TESTE SA;99999;Fato Relevante;;Aquisição de ativo;"
    "2026-09-18;2026-09-18;Ativo;1;123456;https://dados.cvm.gov.br/documento/123456"
)


def test_ipe_le_metadados_do_fato_relevante(tmp_path: Path) -> None:
    path = _csv(tmp_path, "ipe.csv", IPE_HEADER, IPE_FATO)
    (doc,) = list(cvm_documents.parse_documents(read_rows(path)))
    assert doc.protocol == "123456"
    assert doc.cvm_code == 99999
    assert doc.category == "Fato Relevante"
    assert doc.subject == "Aquisição de ativo"
    assert doc.delivered_at == date(2026, 9, 18)
    assert doc.url.startswith("https://dados.cvm.gov.br/")


def test_ipe_descarta_entrega_cancelada(tmp_path: Path) -> None:
    path = _csv(tmp_path, "ipe.csv", IPE_HEADER, IPE_FATO.replace(";Ativo;", ";Cancelado;"))
    assert list(cvm_documents.parse_documents(read_rows(path))) == []


def test_ipe_carga_incremental_por_data_de_entrega(tmp_path: Path) -> None:
    path = _csv(tmp_path, "ipe.csv", IPE_HEADER, IPE_FATO)
    assert list(cvm_documents.parse_documents(read_rows(path), since=date(2026, 9, 19))) == []
    assert len(list(cvm_documents.parse_documents(read_rows(path), since=date(2026, 9, 18)))) == 1


def test_ipe_filtra_categorias_que_nao_sao_comunicado(tmp_path: Path) -> None:
    """Documento periódico já entra pelo DFP/ITR; a aba Comunicados é só o eventual."""
    periodico = IPE_FATO.replace(";Fato Relevante;", ";Dados Econômico-Financeiros;")
    path = _csv(tmp_path, "ipe.csv", IPE_HEADER, periodico)
    assert list(cvm_documents.parse_documents(read_rows(path))) == []
    assert len(list(cvm_documents.parse_documents(read_rows(path), only_relevant=False))) == 1


def test_ipe_nao_baixa_o_documento(tmp_path: Path) -> None:
    """§8.3: o produto lista e linka; quem abre o documento é o usuário, na CVM."""
    pedidos: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        pedidos.append(str(request.url))
        return httpx.Response(200, content=f"{IPE_HEADER}\n{IPE_FATO}\n".encode("latin-1"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    documents = cvm_documents.fetch_year(2026, http=client)

    assert len(documents) == 1
    assert pedidos == [cvm_documents.yearly_url(2026)]


def test_ipe_cai_para_o_zip_quando_o_csv_nao_existe() -> None:
    """A CVM já publicou o conjunto das duas formas; um 404 não pode parar a carga."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ipe_cia_aberta_2026.csv", f"{IPE_HEADER}\n{IPE_FATO}\n")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith(".csv"):
            return httpx.Response(404)
        return httpx.Response(200, content=buffer.getvalue())

    documents = cvm_documents.fetch_year(
        2026, http=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert [d.protocol for d in documents] == ["123456"]


# --- URLs -------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        cvm.COMPANIES_URL,
        cvm.FII_REGISTRY_URL,
        cvm.statements_url(2025),
        cvm.statements_url(2025, period_type="quarterly"),
        cvm.fca_url(2025),
        cvm.fii_monthly_url(2025),
        cvm_documents.yearly_url(2025),
    ],
)
def test_toda_url_da_cvm_aponta_para_o_host_permitido(url: str) -> None:
    from alpherion.data.sources.http import check_host

    check_host(url)  # não levanta
