"""Leitura de campos dos CSVs oficiais brasileiros (CVM, Tesouro, B3).

Os arquivos da CVM têm três armadilhas que aparecem em todo dataset e que não valem ser
reescritas em cada parser:

1. **Encoding latin-1** com `;` como separador — ler como UTF-8 quebra em "AÇÕES".
2. **Nome de coluna instável.** A CVM renomeia colunas entre datasets e entre anos
   (`CNPJ_CIA` no DFP, `CNPJ_Companhia` no IPE; `CD_CVM` e `Codigo_CVM` para o mesmo
   campo). Procurar pela forma normalizada, com apelidos, evita um parser por ano.
3. **Ausência tem significado.** Campo vazio vira `None`, nunca zero: a página mostra
   "—" com o motivo (§3.5), e um zero inventado aqui vira indicador errado na tela.
"""

from __future__ import annotations

import csv
import logging
import unicodedata
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

#: Todo dataset da CVM é latin-1 (ISO-8859-1); nenhum deles migrou para UTF-8.
CVM_ENCODING: Final = "latin-1"
DELIMITER: Final = ";"

#: A CVM usa estes literais para "não informado" — todos equivalem a ausência.
NULL_TOKENS: Final = frozenset({"", "-", "n/a", "na", "nao informado", "nao aplicavel", "null"})


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize_key(name: str) -> str:
    """`Código CVM` → `codigo_cvm`; `CD_CVM` → `cd_cvm`. Chave estável de busca."""
    cleaned = strip_accents(name).strip().lower()
    return "".join(c if c.isalnum() else "_" for c in cleaned).strip("_")


class Row:
    """Uma linha de CSV consultada por nome normalizado, com apelidos.

    `row.get("cd_cvm", "codigo_cvm")` acha a coluna em qualquer um dos nomes que a CVM
    já usou — a primeira que existir e não estiver vazia ganha.
    """

    __slots__ = ("_data",)

    def __init__(self, raw: dict[str, str | None]) -> None:
        self._data = {normalize_key(k): (v or "") for k, v in raw.items() if k}

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def keys(self) -> frozenset[str]:
        return frozenset(self._data)

    def get(self, *names: str) -> str | None:
        """Primeiro valor não vazio entre as colunas dadas; `None` se nenhuma tiver valor."""
        for name in names:
            value = self._data.get(name, "").strip()
            if value and strip_accents(value).lower() not in NULL_TOKENS:
                return value
        return None

    def text(self, *names: str, limit: int | None = None) -> str | None:
        value = self.get(*names)
        return value[:limit] if value and limit else value

    def decimal(self, *names: str) -> Decimal | None:
        """`1.234.567,89` → `Decimal("1234567.89")`. Valor inválido vira `None` com aviso."""
        raw = self.get(*names)
        if raw is None:
            return None
        value = raw.replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return Decimal(value)
        except InvalidOperation:
            logger.warning("valor não numérico em %s: %r", names[0], raw)
            return None

    def integer(self, *names: str) -> int | None:
        value = self.decimal(*names)
        return int(value) if value is not None else None

    def date(self, *names: str) -> date | None:
        """Aceita `aaaa-mm-dd` (formato da CVM) e `dd/mm/aaaa` (Tesouro, B3)."""
        raw = self.get(*names)
        if raw is None:
            return None
        for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(raw[:10], pattern).date()
            except ValueError:
                continue
        logger.warning("data não reconhecida em %s: %r", names[0], raw)
        return None

    def digits(self, *names: str) -> str | None:
        """CNPJ `12.345.678/0001-90` → `12345678000190` (é assim que guardamos)."""
        raw = self.get(*names)
        if raw is None:
            return None
        only = "".join(c for c in raw if c.isdigit())
        return only or None

    def flag(self, *names: str, true: str = "S") -> bool | None:
        raw = self.get(*names)
        if raw is None:
            return None
        return raw.strip().upper() == true.upper()


def read_rows(path: Path, *, encoding: str = CVM_ENCODING) -> Iterator[Row]:
    """Linhas de um CSV oficial, já normalizadas. Lê em streaming: os arquivos são grandes."""
    with path.open(encoding=encoding, newline="", errors="replace") as file:
        for raw in csv.DictReader(file, delimiter=DELIMITER):
            yield Row(raw)
