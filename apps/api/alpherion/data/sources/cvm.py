"""CVM Dados Abertos — cadastro, demonstrações, FCA e informes de FII.

Fonte **liberada** para produção (verificada em 21/09/2026, `docs/fontes-de-dados.md`):
dados abertos do Poder Executivo Federal (Lei 12.527/2011, Decreto 8.777/2016 art. 4),
com atribuição "Fonte: CVM". É a fonte que sustenta o site inteiro sem depender da
licença da B3 (ADR-017): cadastro, demonstrações, indicadores sem preço, FIIs e
comunicados saem no ar mesmo com `MARKET_B3_PRICES_ENABLED=false`.

Cada conjunto é um CSV (cadastro) ou um ZIP por ano (documentos). O download e a
descompressão passam pelas proteções do §7.5 (`sources/http.py`): nenhum arquivo da CVM
é lido de um caminho que o próprio arquivo escolheu.

Os nomes de coluna abaixo vêm dos dicionários publicados com cada conjunto — e a CVM os
renomeia entre datasets (`CD_CVM` nas demonstrações, `Codigo_CVM` no IPE). Por isso a
leitura é por apelido (`csv_fields.Row.get`) e uma coluna que sumir vira `None` com
aviso, não exceção: um campo novo não pode derrubar a carga do dia.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import httpx

from alpherion.data.sources.http import download, extract_all
from alpherion.data.transform.csv_fields import Row, read_rows, strip_accents
from alpherion.data.transform.cvm_statements import (
    ANNUAL,
    QUARTERLY,
    StatementRow,
    latest_versions,
    parse_file,
)

logger = logging.getLogger(__name__)

BASE_URL: Final = "https://dados.cvm.gov.br/dados"

#: Cadastro de companhias abertas (arquivo único, sempre o estado atual).
COMPANIES_URL: Final = f"{BASE_URL}/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
#: Cadastro de FIIs (arquivo único).
FII_REGISTRY_URL: Final = f"{BASE_URL}/FII/CAD/DADOS/cad_fii.csv"

MAX_CSV_BYTES: Final = 200 * 1024 * 1024
MAX_ZIP_BYTES: Final = 150 * 1024 * 1024
#: Um pacote anual de DFP chega a ~1 GB descomprimido somando todas as demonstrações.
MAX_UNCOMPRESSED_BYTES: Final = 1500 * 1024 * 1024

#: `SIT` do cadastro que consideramos ativo; o resto vira `inactive` (§4.3).
ACTIVE_STATUSES: Final = frozenset({"ATIVO", "EM FUNCIONAMENTO NORMAL", "FASE PRE-OPERACIONAL"})


def statements_url(year: int, *, period_type: str = ANNUAL) -> str:
    """Pacote anual da DFP (exercício) ou do ITR (trimestres do ano)."""
    if period_type == ANNUAL:
        return f"{BASE_URL}/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"
    return f"{BASE_URL}/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{year}.zip"


def fre_url(year: int) -> str:
    """Formulário de Referência: é nele (não no FCA) que está o capital social."""
    return f"{BASE_URL}/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_{year}.zip"


def fca_url(year: int) -> str:
    """Formulário Cadastral: capital social e quantidade de ações em circulação."""
    return f"{BASE_URL}/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{year}.zip"


def fii_monthly_url(year: int) -> str:
    return f"{BASE_URL}/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{year}.zip"


# --- cadastro de companhias -------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompanyRow:
    """Companhia aberta registrada na CVM.

    Não tem ticker: a ligação com `securities` é pelo `cvm_code` (PETR3 e PETR4 são a
    mesma companhia) e, quando ele falta, pelo CNPJ.
    """

    cvm_code: int
    cnpj: str | None
    company_name: str
    trade_name: str | None
    #: Setor de atividade da CVM — mais grosso que o segmento B3, que é o que usamos
    #: em `/setores`. Serve de fallback enquanto a listagem da B3 não carrega.
    cvm_sector: str | None
    status: str
    registered_at: date | None
    ri_url: str | None


def parse_companies(rows: Iterator[Row]) -> Iterator[CompanyRow]:
    for row in rows:
        cvm_code = row.integer("cd_cvm", "codigo_cvm")
        name = row.text("denom_social", "denominacao_social", limit=200)
        if cvm_code is None or name is None:
            continue
        situation = strip_accents(row.get("sit", "situacao") or "").strip().upper()
        yield CompanyRow(
            cvm_code=cvm_code,
            cnpj=row.digits("cnpj_cia", "cnpj_companhia"),
            company_name=name,
            trade_name=row.text("denom_comerc", "denominacao_comercial", limit=200),
            cvm_sector=row.text("setor_ativ", "setor_atividade", limit=120),
            status="active" if situation in ACTIVE_STATUSES else "inactive",
            registered_at=row.date("dt_reg", "data_registro"),
            ri_url=row.text("site", "pagina_web"),
        )


def fetch_companies(*, http: httpx.Client | None = None) -> Iterator[CompanyRow]:
    """Cadastro completo das companhias abertas. Consuma o gerador dentro do contexto."""
    with _downloaded_csv(COMPANIES_URL, "cad_cia_aberta.csv", http) as path:
        yield from parse_companies(read_rows(path))


# --- cadastro de FIIs -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FiiRow:
    """Fundo imobiliário no cadastro da CVM. O ticker vem da listagem da B3."""

    cnpj: str
    name: str
    trade_name: str | None
    #: Segmento informado pelo fundo (tijolo, papel, híbrido, FoF) — filtro de `/fiis`.
    segment: str | None
    status: str
    manager: str | None
    administrator: str | None
    started_at: date | None
    target_audience: str | None


def parse_fii_registry(rows: Iterator[Row]) -> Iterator[FiiRow]:
    for row in rows:
        cnpj = row.digits("cnpj_fundo", "cnpj_cia")
        name = row.text("denominacao_social", "nome_fundo", limit=200)
        if cnpj is None or name is None:
            continue
        situation = strip_accents(row.get("situacao") or "").strip().upper()
        yield FiiRow(
            cnpj=cnpj,
            name=name,
            trade_name=row.text("nome_comercial", limit=200),
            segment=row.text("segmento", "setor_atividade", limit=60),
            status="active" if situation in ACTIVE_STATUSES else "inactive",
            manager=row.text("gestor", "nome_gestor", limit=200),
            administrator=row.text("administrador", "nome_administrador", limit=200),
            started_at=row.date("data_registro", "data_constituicao"),
            target_audience=row.text("publico_alvo", limit=120),
        )


def fetch_fii_registry(*, http: httpx.Client | None = None) -> Iterator[FiiRow]:
    with _downloaded_csv(FII_REGISTRY_URL, "cad_fii.csv", http) as path:
        yield from parse_fii_registry(read_rows(path))


# --- informes mensais de FII ------------------------------------------------


@dataclass(frozen=True, slots=True)
class FiiReportRow:
    """Informe mensal de um FII, por CNPJ.

    A tabela `fii_reports` é por ticker; a conversão CNPJ → ticker é do job, que tem o
    cadastro de `securities` à mão. Aqui não inventamos ticker.

    Quase tudo é opcional porque o fundo informa o que quer: vacância só aparece em
    fundo de tijolo, e a página mostra "—" com o motivo quando falta (§3.5).
    """

    cnpj: str
    period: date
    version: int
    nav: Decimal | None
    nav_per_share: Decimal | None
    shares: Decimal | None
    shareholders: int | None
    income_per_share: Decimal | None
    vacancy_physical: Decimal | None
    vacancy_financial: Decimal | None
    admin_fee: Decimal | None
    manager: str | None
    administrator: str | None
    segment: str | None
    #: ISIN da cota — o vínculo com o ticker. O cadastro de instrumentos da B3 traz o
    #: ISIN, mas não o CNPJ do fundo.
    isin: str | None = None
    #: `Mercado_Negociacao_Bolsa`: a cota negocia na B3. Desempata quando dois fundos
    #: declaram o mesmo ISIN (acontece: erro de cadastro na CVM).
    exchange_listed: bool | None = None


def parse_fii_monthly(rows: Iterator[Row]) -> Iterator[FiiReportRow]:
    """Lê um dos CSVs do informe mensal (geral, ativo/passivo, complemento).

    Os três arquivos compartilham (CNPJ, data de referência, versão) e trazem recortes
    diferentes do mesmo informe — `merge_fii_reports` junta o que cada um tem.
    """
    # Desde a Resolução CVM 175 (2025) as colunas falam em "Fundo_Classe"
    # (`CNPJ_Fundo_Classe`, `Segmento_Atuacao`, `Total_Numero_Cotistas`); os nomes antigos
    # ficam como apelido para reprocessar anos anteriores.
    for row in rows:
        cnpj = row.digits("cnpj_fundo_classe", "cnpj_fundo", "cnpj_cia")
        period = row.date("data_referencia", "dt_refer")
        if cnpj is None or period is None:
            continue
        isin = row.text("codigo_isin", "isin", limit=12)
        yield FiiReportRow(
            cnpj=cnpj,
            # O informe é mensal: normalizamos para o 1º dia do mês, que é a chave.
            period=period.replace(day=1),
            version=row.integer("versao") or 1,
            nav=row.decimal("patrimonio_liquido", "valor_patrimonio_liquido"),
            nav_per_share=row.decimal("valor_patrimonial_cotas", "valor_patrimonial_cota"),
            shares=row.decimal("cotas_emitidas", "quantidade_cotas_emitidas"),
            shareholders=row.integer(
                "total_numero_cotistas", "quantidade_cotistas", "numero_cotistas"
            ),
            income_per_share=row.decimal("valor_rendimento_cota", "rendimento_cota"),
            vacancy_physical=row.decimal("percentual_vacancia_fisica"),
            vacancy_financial=row.decimal("percentual_vacancia_financeira"),
            admin_fee=row.decimal("percentual_despesas_taxa_administracao"),
            manager=row.text("gestor", "nome_gestor", limit=200),
            administrator=row.text("nome_administrador", "administrador", limit=200),
            segment=row.text("segmento_atuacao", "segmento", limit=60),
            # "0" e vazio são o marcador da CVM para fundo sem cota listada.
            isin=isin.upper() if isin and len(isin) == 12 else None,
            exchange_listed=row.flag("mercado_negociacao_bolsa"),
        )


#: Campos que os três arquivos do informe preenchem em partes.
_FII_REPORT_FIELDS: Final = (
    "nav",
    "nav_per_share",
    "shares",
    "shareholders",
    "income_per_share",
    "vacancy_physical",
    "vacancy_financial",
    "admin_fee",
    "manager",
    "administrator",
    "segment",
    "isin",
    "exchange_listed",
)


def merge_fii_reports(rows: Iterator[FiiReportRow]) -> list[FiiReportRow]:
    """Junta os recortes do mesmo informe e fica com a maior versão.

    Regra do merge: campo preenchido nunca é apagado por um vazio de outro arquivo; uma
    versão maior manda no que trouxer, e só o que ela deixa vazio é completado pela
    anterior. É o que torna a carga idempotente — reprocessar o ano inteiro dá o mesmo
    resultado, em qualquer ordem de arquivo.
    """
    merged: dict[tuple[str, date], FiiReportRow] = {}
    for row in rows:
        key = (row.cnpj, row.period)
        current = merged.get(key)
        if current is None:
            merged[key] = row
            continue
        base, other = (row, current) if row.version >= current.version else (current, row)
        values = {
            field: (
                getattr(base, field) if getattr(base, field) is not None else getattr(other, field)
            )
            for field in _FII_REPORT_FIELDS
        }
        merged[key] = FiiReportRow(cnpj=key[0], period=key[1], version=base.version, **values)
    return list(merged.values())


def fetch_fii_monthly(year: int, *, http: httpx.Client | None = None) -> list[FiiReportRow]:
    """Informes mensais de um ano, já juntados por fundo e mês."""
    with _downloaded_zip(fii_monthly_url(year), f"inf_mensal_fii_{year}.zip", http) as files:
        rows = (row for path in files for row in parse_fii_monthly(read_rows(path)))
        reports = merge_fii_reports(rows)
    logger.info("informes de FII %d: %d fundos-mês", year, len(reports))
    return reports


# --- FRE: capital social e ações em circulação ------------------------------


@dataclass(frozen=True, slots=True)
class CompanyFactRow:
    """Linha de `company_facts`: o que transforma lucro em LPA e preço em market cap.

    O arquivo do FRE identifica a companhia pelo **CNPJ** (não traz código CVM); quem
    converte para `cvm_code` é o job, com o cadastro à mão.
    """

    cnpj: str | None
    cvm_code: int | None
    reference_date: date
    shares_outstanding: Decimal | None
    capital_social: Decimal | None
    version: int
    #: Fração das ações em circulação (fora de controladores e tesouraria), do arquivo
    #: `distribuicao_capital`: 0,612 = 61,2%.
    free_float: Decimal | None = None


def parse_free_float(rows: Iterator[Row]) -> Iterator[tuple[str, date, int, Decimal]]:
    """Lê `fre_cia_aberta_distribuicao_capital_<ano>.csv`: (CNPJ, data, versão, fração).

    A CVM publica o percentual em pontos (`61.212000`); guardamos fração, como toda
    razão do produto.
    """
    for row in rows:
        cnpj = row.digits("cnpj_companhia", "cnpj_cia")
        reference = row.date("data_referencia", "dt_refer")
        percent = row.decimal("percentual_total_acoes_circulacao")
        if cnpj is None or reference is None or percent is None:
            continue
        if not Decimal(0) <= percent <= Decimal(100):
            continue  # percentual fora de 0–100 é erro de digitação no formulário
        yield cnpj, reference, row.integer("versao") or 1, percent / Decimal(100)


def parse_company_facts(rows: Iterator[Row]) -> Iterator[CompanyFactRow]:
    """Lê `fre_cia_aberta_capital_social_<ano>.csv`.

    O arquivo tem uma linha por tipo de capital (autorizado, emitido, subscrito,
    integralizado); ficamos com o **integralizado**, que é o que existe de fato. Sem ele,
    a linha não vira fato nenhum — melhor faltar o indicador do que publicar market cap
    errado.
    """
    for row in rows:
        cnpj = row.digits("cnpj_companhia", "cnpj_cia")
        cvm_code = row.integer("codigo_cvm", "cd_cvm")
        reference = row.date("data_referencia", "dt_refer")
        if (cnpj is None and cvm_code is None) or reference is None:
            continue
        kind = strip_accents(row.get("tipo_capital") or "").strip().upper()
        if "INTEGRALIZADO" not in kind:
            continue
        yield CompanyFactRow(
            cnpj=cnpj,
            cvm_code=cvm_code,
            reference_date=reference,
            shares_outstanding=row.decimal("quantidade_total_acoes", "quantidade_acoes"),
            capital_social=row.decimal("valor_capital", "valor_capital_social"),
            version=row.integer("versao") or 1,
        )


def fetch_company_facts(year: int, *, http: httpx.Client | None = None) -> list[CompanyFactRow]:
    """Capital social e free float do FRE do ano, uma linha por companhia (maior versão).

    O filtro é o nome exato dos dois arquivos: o ZIP traz também `capital_social_classe_acao`,
    `distribuicao_capital_classe_acao` e outros, com colunas diferentes.
    """
    capital_file = f"capital_social_{year}"
    float_file = f"distribuicao_capital_{year}"
    with _downloaded_zip(
        fre_url(year), f"fre_{year}.zip", http, match=(capital_file, float_file)
    ) as files:
        facts: dict[tuple[str, date], CompanyFactRow] = {}
        floats: dict[tuple[str, date], tuple[int, Decimal]] = {}
        for path in files:
            if float_file in path.name:
                for cnpj, reference, version, value in parse_free_float(read_rows(path)):
                    current = floats.get((cnpj, reference))
                    if current is None or version > current[0]:
                        floats[(cnpj, reference)] = (version, value)
                continue
            for fact in parse_company_facts(read_rows(path)):
                key = (fact.cnpj or str(fact.cvm_code), fact.reference_date)
                existing = facts.get(key)
                if existing is None or fact.version > existing.version:
                    facts[key] = fact
    merged = [
        replace(fact, free_float=floats[key][1]) if key in floats else fact
        for key, fact in facts.items()
    ]
    logger.info(
        "FRE %d: %d fatos de capital social, %d com free float", year, len(merged), len(floats)
    )
    return merged


# --- demonstrações ----------------------------------------------------------


def fetch_statements(
    year: int,
    *,
    period_type: str = ANNUAL,
    http: httpx.Client | None = None,
) -> list[StatementRow]:
    """DFP (ou ITR) de um ano, já com a versão mais recente de cada conta.

    Devolve lista e não gerador porque a dedupe por versão precisa do pacote inteiro:
    a republicação pode estar em qualquer lugar do arquivo.
    """
    if period_type not in (ANNUAL, QUARTERLY):
        raise ValueError(f"period_type inválido: {period_type!r}")
    url = statements_url(year, period_type=period_type)
    with _downloaded_zip(url, f"cvm_{period_type}_{year}.zip", http) as files:
        rows = (row for path in files for row in parse_file(path, period_type=period_type))
        statements = latest_versions(rows)
    logger.info("demonstrações CVM %s %d: %d linhas", period_type, year, len(statements))
    return statements


# --- download ---------------------------------------------------------------


@contextmanager
def _downloaded_csv(url: str, name: str, http: httpx.Client | None) -> Iterator[Path]:
    """Baixa um CSV para um temporário apagado na saída.

    Nada da CVM fica em disco depois da carga: o que interessa está no banco, e cópia de
    arquivo de terceiro só aumenta superfície (§7.5).
    """
    with TemporaryDirectory(prefix="alpherion-cvm-") as tmp:
        yield download(url, Path(tmp) / name, max_bytes=MAX_CSV_BYTES, http=http)


@contextmanager
def _downloaded_zip(
    url: str,
    name: str,
    http: httpx.Client | None,
    *,
    match: str | tuple[str, ...] | None = None,
) -> Iterator[list[Path]]:
    with TemporaryDirectory(prefix="alpherion-cvm-") as tmp:
        tmp_path = Path(tmp)
        zip_path = download(url, tmp_path / name, max_bytes=MAX_ZIP_BYTES, http=http)
        yield extract_all(zip_path, tmp_path / "csv", max_bytes=MAX_UNCOMPRESSED_BYTES, match=match)
