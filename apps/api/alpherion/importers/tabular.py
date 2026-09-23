"""Leitura segura de planilha (xlsx) e CSV enviados pelo usuário (site.md §7.4).

Tudo em memória; nada vai para disco nem para log. As defesas, na ordem em que o
arquivo passa por elas:

1. **Tamanho** do envio (`MAX_FILE_BYTES`) e **conteúdo, não extensão**: xlsx é um ZIP
   (`PK\\x03\\x04`) com `[Content_Types].xml`; o resto é tratado como texto (CSV).
2. **Zip bomb**: soma do tamanho **descomprimido** declarado das entradas e número de
   entradas limitados antes de abrir; a leitura do openpyxl é em `read_only`.
3. **Sem macros**: `vbaProject.bin` ou tipo `macroEnabled` → recusado.
4. **Limites de linhas, colunas e células** por planilha.
5. **Colunas permitidas**: `find_table` localiza o cabeçalho e devolve **só** as
   colunas pedidas pelo parser. CPF, nome do titular, conta e instituição — que os
   arquivos da Área do Investidor trazem — nunca entram nos dicionários de saída.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from openpyxl import load_workbook

MAX_FILE_BYTES: Final = 5 * 1024 * 1024
MAX_CSV_BYTES: Final = 2 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES: Final = 50 * 1024 * 1024
MAX_ZIP_ENTRIES: Final = 500
MAX_SHEETS: Final = 20
MAX_ROWS: Final = 20_000
MAX_COLUMNS: Final = 60
MAX_CELLS: Final = 400_000
#: Quantas linhas do topo olhar atrás do cabeçalho (a B3 põe título e data antes).
HEADER_SCAN_ROWS: Final = 25


class ImportFileError(ValueError):
    """Arquivo recusado. A mensagem vai para o usuário — nunca com conteúdo do arquivo."""


@dataclass(frozen=True, slots=True)
class Sheet:
    name: str
    rows: list[tuple[Any, ...]]


# --- leitura ----------------------------------------------------------------


def read_file(data: bytes, *, max_bytes: int = MAX_FILE_BYTES) -> list[Sheet]:
    """xlsx ou CSV → planilhas com linhas cruas. Recusa o que passar dos limites."""
    if not data:
        raise ImportFileError("arquivo vazio")
    if len(data) > max_bytes:
        raise ImportFileError(f"arquivo maior que {max_bytes // (1024 * 1024)} MB")
    if data[:4] == b"PK\x03\x04":
        return _read_xlsx(data)
    return [_read_csv(data)]


def _read_xlsx(data: bytes) -> list[Sheet]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ZIP_ENTRIES:
                raise ImportFileError("planilha com estrutura fora do padrão (entradas demais)")
            if sum(e.file_size for e in entries) > MAX_UNCOMPRESSED_BYTES:
                raise ImportFileError("planilha grande demais depois de descomprimida")
            names = {e.filename.lower() for e in entries}
            if "[content_types].xml" not in names:
                raise ImportFileError("o arquivo não é uma planilha xlsx válida")
            if any("vbaproject" in n for n in names) or b"macroEnabled" in archive.read(
                "[Content_Types].xml"
            ):
                raise ImportFileError("planilha com macros não é aceita")
    except zipfile.BadZipFile as error:
        raise ImportFileError("o arquivo não é uma planilha xlsx válida") from error

    try:
        workbook = load_workbook(
            io.BytesIO(data), read_only=True, data_only=True, keep_vba=False, keep_links=False
        )
    except Exception as error:  # openpyxl levanta vários tipos para arquivo corrompido
        raise ImportFileError("não foi possível ler a planilha") from error

    sheets: list[Sheet] = []
    cells = 0
    try:
        for worksheet in workbook.worksheets[:MAX_SHEETS]:
            rows: list[tuple[Any, ...]] = []
            for index, row in enumerate(worksheet.iter_rows(values_only=True, max_col=MAX_COLUMNS)):
                if index >= MAX_ROWS:
                    raise ImportFileError(f"planilha com mais de {MAX_ROWS} linhas")
                cells += len(row)
                if cells > MAX_CELLS:
                    raise ImportFileError("planilha com células demais")
                rows.append(tuple(row))
            sheets.append(Sheet(name=worksheet.title, rows=rows))
    finally:
        workbook.close()
    return sheets


def _read_csv(data: bytes) -> Sheet:
    if len(data) > MAX_CSV_BYTES:
        raise ImportFileError(f"CSV maior que {MAX_CSV_BYTES // (1024 * 1024)} MB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    if "\x00" in text:
        raise ImportFileError("o arquivo não é CSV nem xlsx")
    sample = text[:4096]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    rows: list[tuple[Any, ...]] = []
    for index, row in enumerate(csv.reader(io.StringIO(text), delimiter=delimiter)):
        if index >= MAX_ROWS:
            raise ImportFileError(f"CSV com mais de {MAX_ROWS} linhas")
        rows.append(tuple(row[:MAX_COLUMNS]))
    return Sheet(name="csv", rows=rows)


# --- cabeçalho e colunas permitidas ----------------------------------------


def norm(value: Any) -> str:
    """`Código de Negociação` → `codigo de negociacao` (sem acento, caixa, pontuação)."""
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    return " ".join(re.sub(r"[^a-z0-9/]+", " ", text).split())


@dataclass(frozen=True, slots=True)
class Table:
    """Uma tabela achada numa planilha: onde começa e que coluna é cada campo."""

    header_row: int
    columns: dict[str, int]
    rows: list[tuple[Any, ...]]

    def records(self) -> Iterator[tuple[int, dict[str, Any]]]:
        """(número da linha na planilha, {campo: valor}) — **só** os campos mapeados."""
        for offset, row in enumerate(self.rows[self.header_row + 1 :], start=self.header_row + 2):
            if not any(cell not in (None, "") for cell in row):
                continue
            yield (
                offset,
                {
                    name: (row[index] if index < len(row) else None)
                    for name, index in self.columns.items()
                },
            )


def find_table(
    sheet: Sheet,
    required: Mapping[str, Sequence[str]],
    optional: Mapping[str, Sequence[str]] | None = None,
) -> Table | None:
    """Acha o cabeçalho que tem **todos** os campos obrigatórios (por apelido).

    Devolve só as colunas dos campos pedidos; qualquer outra coluna da planilha —
    inclusive CPF e nome — fica de fora da tabela e, portanto, de tudo que vem depois.
    """
    wanted = {**required, **(optional or {})}
    for index, row in enumerate(sheet.rows[:HEADER_SCAN_ROWS]):
        labels = [norm(cell) for cell in row]
        columns: dict[str, int] = {}
        for field_name, aliases in wanted.items():
            # Apelidos em ordem de preferência: "Valor Atualizado CURVA" antes do "MTM".
            for alias in (norm(a) for a in aliases):
                position = next(
                    (
                        i
                        for i, label in enumerate(labels)
                        if label == alias and i not in columns.values()
                    ),
                    None,
                )
                if position is not None:
                    columns[field_name] = position
                    break
        if all(name in columns for name in required):
            return Table(header_row=index, columns=columns, rows=sheet.rows)
    return None


# --- valores ----------------------------------------------------------------


#: Casas decimais máximas (o `web` guarda e compara com até 10).
MAX_PLACES: Final = Decimal("1e-10")


def _clamp(value: Decimal) -> Decimal | None:
    """Sem expoente na saída (`1E+2` → `100`) e no máximo 10 casas (float do Excel traz
    `0.30000000000000004`). Infinito e NaN → None."""
    if not value.is_finite():
        return None
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        return value.quantize(Decimal(1))
    if isinstance(exponent, int) and exponent < -10:
        return value.quantize(MAX_PLACES)
    return value


def parse_decimal(value: Any) -> Decimal | None:
    """`R$ 1.234,56`, `1234.56`, `38,5` e número do Excel → Decimal. Vazio/`-` → None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float | Decimal):
        return _clamp(Decimal(repr(value)) if isinstance(value, float) else Decimal(value))
    text = str(value).strip().replace("R$", "").replace("\xa0", "").replace(" ", "")
    if text in ("", "-", "--"):
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return _clamp(Decimal(text))
    except InvalidOperation:
        return None


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    return None


TICKER_RE: Final = re.compile(r"^[A-Z0-9]{4}\d{1,2}[A-Z]?$")


def parse_ticker(value: Any) -> str | None:
    """`PETR4F` (fracionário) → `PETR4`; `PETR4 - PETROBRAS` → `PETR4`. Inválido → None."""
    text = str(value or "").strip().upper()
    if " - " in text:
        text = text.split(" - ", 1)[0].strip()
    text = text.split()[0] if text else text
    if not TICKER_RE.match(text):
        return None
    if re.match(r"^[A-Z0-9]{4}\d{1,2}F$", text):
        text = text[:-1]
    return text
