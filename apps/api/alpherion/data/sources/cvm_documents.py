"""CVM IPE — documentos entregues pelas companhias (fato relevante, comunicado, aviso).

Alimenta a aba "Comunicados" da página do ativo e a tab Eventos de `/mercado`. Fonte
liberada (dados abertos, mesma política do conjunto CVM — `docs/fontes-de-dados.md`).

**Este módulo nunca baixa o documento.** Só o CSV de metadados; o link aponta para o
arquivo na CVM. Site.md §8.3: resumir fato relevante é interpretação, e interpretação é
análise (Res. CVM 20). O produto lista título, categoria, data e link — nada mais.

O conjunto é um CSV por ano (`ipe_cia_aberta_2026.csv`), publicado ora solto, ora
dentro de um ZIP de mesmo nome. A carga é incremental por **data de entrega**: o job
guarda a última carregada e relê a partir dela, porque uma entrega pode aparecer no
arquivo depois da data (protocolo em análise).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import httpx

from alpherion.data.sources.http import SourceError, download, extract_all
from alpherion.data.transform.csv_fields import Row, read_rows, strip_accents

logger = logging.getLogger(__name__)

BASE_URL: Final = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS"
MAX_DOWNLOAD_BYTES: Final = 80 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES: Final = 400 * 1024 * 1024

#: Categorias que viram "Comunicados" na página do ativo. O IPE traz muito mais
#: (documentos periódicos, dados econômico-financeiros), que já entram pelo DFP/ITR.
RELEVANT_CATEGORIES: Final = frozenset(
    {
        "fato relevante",
        "comunicado ao mercado",
        "aviso aos acionistas",
        "assembleia",
        "calendario de eventos corporativos",
        "politica de negociacao de valores mobiliarios",
        "acordo de acionistas",
        "reuniao da administracao",
    }
)

#: `numSequencia` do link de download: identifica o documento quando o protocolo falta.
SEQUENCE_RE: Final = re.compile(r"[?&]numSequencia=(\d+)")

#: Só o protocolo cancelado sai da lista; "ativo" e "reapresentado" ficam.
CANCELLED: Final = "cancelado"


@dataclass(frozen=True, slots=True)
class DocumentRow:
    """Metadados de um documento entregue à CVM, prontos para `company_documents`."""

    protocol: str
    cvm_code: int
    cnpj: str | None
    category: str
    type: str | None
    subject: str | None
    delivered_at: date
    reference_date: date | None
    url: str


def yearly_url(year: int, *, zipped: bool = False) -> str:
    suffix = "zip" if zipped else "csv"
    return f"{BASE_URL}/ipe_cia_aberta_{year}.{suffix}"


def _protocol(row: Row) -> str | None:
    """Identificador estável da entrega.

    O IPE traz `Protocolo_Entrega`; em anos antigos, só o `Id_Documento`. Algumas
    entregas (≈1,5% de 2026, muitas de "Relatório Proventos") vêm com os dois vazios —
    aí vale o `numSequencia` do link da CVM, que é único por documento. É o que garante
    que reprocessar o ano não duplique a lista.
    """
    protocol = row.text("protocolo_entrega", "id_documento", "protocolo", limit=40)
    if protocol:
        return protocol
    link = row.get("link_download", "url_documento", "link") or ""
    match = SEQUENCE_RE.search(link)
    return f"seq-{match.group(1)}" if match else None


def parse_documents(
    rows: Iterator[Row],
    *,
    since: date | None = None,
    only_relevant: bool = True,
) -> Iterator[DocumentRow]:
    """Converte o CSV do IPE, descartando entrega cancelada e anterior a `since`."""
    for row in rows:
        protocol = _protocol(row)
        cvm_code = row.integer("codigo_cvm", "cd_cvm")
        delivered = row.date("data_entrega", "dt_entrega")
        url = row.get("link_download", "url_documento", "link")
        category = row.text("categoria", limit=120)
        if protocol is None or cvm_code is None or delivered is None or url is None:
            continue
        if category is None:
            continue
        if since is not None and delivered < since:
            continue
        status = (row.get("status") or "").strip().lower()
        if status.startswith(CANCELLED):
            continue
        if only_relevant and not is_relevant(category):
            continue
        yield DocumentRow(
            protocol=protocol,
            cvm_code=cvm_code,
            cnpj=row.digits("cnpj_companhia", "cnpj_cia"),
            category=category,
            type=row.text("tipo", limit=120),
            subject=row.text("assunto", "especie"),
            delivered_at=delivered,
            reference_date=row.date("data_referencia", "dt_refer"),
            url=url,
        )


def unique_by_protocol(documents: Iterable[DocumentRow]) -> list[DocumentRow]:
    """Um documento por protocolo.

    O arquivo anual da CVM repete linhas inteiras (121 protocolos em 2026), e o upsert
    não aceita a mesma chave duas vezes no mesmo lote. Fica a entrega mais recente.
    """
    unique: dict[str, DocumentRow] = {}
    for document in documents:
        current = unique.get(document.protocol)
        if current is None or document.delivered_at >= current.delivered_at:
            unique[document.protocol] = document
    return list(unique.values())


def is_relevant(category: str) -> bool:
    return strip_accents(category).strip().lower() in RELEVANT_CATEGORIES


def fetch_year(
    year: int,
    *,
    since: date | None = None,
    only_relevant: bool = True,
    http: httpx.Client | None = None,
) -> list[DocumentRow]:
    """Documentos de um ano. `since` faz a carga diária ler só a cauda do arquivo.

    Tenta o CSV solto e cai para o ZIP: a CVM já publicou o conjunto das duas formas, e
    um 404 aqui não pode parar a carga do dia.
    """
    with TemporaryDirectory(prefix="alpherion-ipe-") as tmp:
        tmp_path = Path(tmp)
        try:
            path = download(
                yearly_url(year),
                tmp_path / f"ipe_{year}.csv",
                max_bytes=MAX_DOWNLOAD_BYTES,
                http=http,
            )
        except SourceError as error:
            logger.info("IPE %d: CSV solto indisponível (%s); tentando o ZIP", year, error)
            zip_path = download(
                yearly_url(year, zipped=True),
                tmp_path / f"ipe_{year}.zip",
                max_bytes=MAX_DOWNLOAD_BYTES,
                http=http,
            )
            path = extract_all(zip_path, tmp_path / "csv", max_bytes=MAX_UNCOMPRESSED_BYTES)[0]
        documents = unique_by_protocol(
            parse_documents(read_rows(path), since=since, only_relevant=only_relevant)
        )
    logger.info("IPE %d: %d documentos desde %s", year, len(documents), since or "início do ano")
    return documents
