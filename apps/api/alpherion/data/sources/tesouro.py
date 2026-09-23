"""Tesouro Direto — preços e taxas (Tesouro Transparente).

Licença **ODbL**, verificada em 21/09/2026 (`docs/fontes-de-dados.md`): esta fonte está
liberada para produção. É a única fonte de preço do v1.0 que não depende da B3, então
`/tesouro` sai no ar mesmo com `MARKET_B3_PRICES_ENABLED=false` (ADR-017).

O CSV é um arquivo único com a série inteira (todos os títulos, todos os dias): ~40 MB,
separador `;`, decimal com vírgula, datas em dd/mm/aaaa.
"""

from __future__ import annotations

import csv
import logging
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import httpx

from alpherion.data.sources.http import download

logger = logging.getLogger(__name__)

CSV_URL: Final = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)
MAX_DOWNLOAD_BYTES: Final = 200 * 1024 * 1024
ENCODING: Final = "latin-1"

#: Nome do título na fonte → tipo de indexador que usamos em `treasury_bonds`.
INDEX_TYPES: Final[dict[str, str]] = {
    "TESOURO SELIC": "selic",
    "TESOURO IPCA": "ipca",
    "TESOURO PREFIXADO": "prefixado",
    # Títulos antigos (a série histórica vai até 2005): sem esta regra caíam em "selic".
    "TESOURO IGPM": "igpm",
    "TESOURO RENDA": "renda_mais",
    "TESOURO EDUCA": "educa_mais",
}


@dataclass(frozen=True, slots=True)
class TreasuryRow:
    """Uma linha do CSV: um título em um dia."""

    slug: str
    name: str
    index_type: str
    maturity: date
    #: Paga juros semestrais (o nome traz "com Juros Semestrais").
    coupon: bool
    date: date
    buy_rate: Decimal | None
    sell_rate: Decimal | None
    buy_price: Decimal | None
    sell_price: Decimal | None


def slugify(name: str, maturity: date) -> str:
    """`Tesouro IPCA+ 2029` + 2029-05-15 → `ipca-2029-05-15`.

    A data inteira entra no slug porque existem vencimentos diferentes no mesmo ano
    (com e sem juros semestrais), e a URL precisa ser única e estável.
    """
    index_type = detect_index_type(name)
    suffix = "-juros" if has_coupon(name) else ""
    return f"{index_type}-{maturity:%Y-%m-%d}{suffix}".replace("_", "-")


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def detect_index_type(name: str) -> str:
    upper = _strip_accents(name).upper()
    for prefix, index_type in INDEX_TYPES.items():
        if upper.startswith(prefix):
            return index_type
    if "PREFIXADO" in upper:
        return "prefixado"
    # Nome novo que ninguém mapeou: melhor "outro" com aviso do que chutar um indexador.
    logger.warning("indexador não reconhecido no nome do título: %r", name)
    return "outro"


def has_coupon(name: str) -> bool:
    return "JUROS SEMESTRAIS" in _strip_accents(name).upper()


def _decimal(raw: str) -> Decimal | None:
    """`41,20` → Decimal("41.20"). Campo vazio vira None (não zero)."""
    value = raw.strip().replace(".", "").replace(",", ".")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _date(raw: str) -> date:
    return datetime.strptime(raw.strip(), "%d/%m/%Y").date()


def parse_csv(lines: Iterator[str]) -> Iterator[TreasuryRow]:
    """Lê o CSV do Tesouro Transparente (cabeçalho com nomes por extenso)."""
    reader = csv.DictReader(lines, delimiter=";")
    for row in reader:
        name = (row.get("Tipo Titulo") or "").strip()
        raw_maturity = row.get("Data Vencimento") or ""
        raw_date = row.get("Data Base") or ""
        if not name or not raw_maturity.strip() or not raw_date.strip():
            continue
        maturity = _date(raw_maturity)
        yield TreasuryRow(
            slug=slugify(name, maturity),
            name=name,
            index_type=detect_index_type(name),
            maturity=maturity,
            coupon=has_coupon(name),
            date=_date(raw_date),
            buy_rate=_decimal(row.get("Taxa Compra Manha", "")),
            sell_rate=_decimal(row.get("Taxa Venda Manha", "")),
            buy_price=_decimal(row.get("PU Compra Manha", "")),
            sell_price=_decimal(row.get("PU Venda Manha", "")),
        )


def fetch(*, http: httpx.Client | None = None) -> Iterator[TreasuryRow]:
    """Baixa o CSV e devolve as linhas. Consome o gerador antes de sair do contexto."""
    with TemporaryDirectory(prefix="alpherion-tesouro-") as tmp:
        path = download(CSV_URL, Path(tmp) / "tesouro.csv", max_bytes=MAX_DOWNLOAD_BYTES, http=http)
        with path.open(encoding=ENCODING, newline="") as file:
            yield from parse_csv(file)
