"""O que os importadores devolvem (site.md §2.3, `POST /v1/imports/*/preview`).

A API **não grava nada**: devolve uma prévia normalizada que o `web` mostra, a pessoa
confirma e o `web` cifra e grava no schema `app`. Números saem como string decimal
(`Decimal` no JSON do pydantic), para o `web` não passar por ponto flutuante.

Nenhum modelo aqui tem campo para CPF, nome do titular, conta ou instituição: o que não
tem campo não tem como vazar para a resposta.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

AssetClass = Literal[
    "crypto", "stablecoin", "stock_br", "bdr", "etf_br", "fii", "fixed_income", "treasury", "other"
]
MarketRef = Literal["ticker", "coingecko_id", "treasury_slug", "none"]
FileKind = Literal["b3_posicao", "b3_negociacao", "b3_proventos", "csv"]
IncomeKind = Literal["dividend", "jcp", "fii_income", "interest", "other"]


class AssetRef(BaseModel):
    """Como o `web` identifica o ativo em `app.assets` (classe + símbolo)."""

    symbol: str
    name: str
    asset_class: AssetClass
    market_ref: MarketRef
    #: `False` quando o ativo não está no cadastro de mercado (a pessoa confere na prévia).
    known: bool = True


class RowRef(BaseModel):
    """De onde veio a linha — para o aviso apontar "arquivo 2, aba Ações, linha 14"."""

    file: int
    sheet: str
    row: int


class ParsedTransaction(BaseModel):
    origin: RowRef
    asset: AssetRef
    date: date
    side: Literal["buy", "sell"]
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal(0)
    #: 1 na primeira linha idêntica (ativo, data, tipo, qtd, preço) do envio, 2 na
    #: segunda... Duas execuções iguais no mesmo dia são negócios distintos; o `web`
    #: inclui o número na chave de dedupe para não descartar a segunda como repetida.
    occurrence: int = 1


class ParsedIncome(BaseModel):
    origin: RowRef
    asset: AssetRef
    date: date
    kind: IncomeKind
    #: Bruto só quando o arquivo traz (JCP vem líquido de IR na B3).
    gross: Decimal | None = None
    net: Decimal
    occurrence: int = 1


class ParsedPosition(BaseModel):
    """Posição atual informada pelo arquivo de posição: vira `position_adjustments`."""

    origin: RowRef
    asset: AssetRef
    quantity: Decimal | None = None
    value_brl: Decimal | None = None
    avg_price: Decimal | None = None


class RowWarning(BaseModel):
    origin: RowRef | None = None
    message: str


class FileSummary(BaseModel):
    file: int
    kind: FileKind | None
    rows_in: int
    rows_ok: int
    rows_skipped: int


class ImportPreview(BaseModel):
    files: list[FileSummary]
    transactions: list[ParsedTransaction] = Field(default_factory=list)
    income: list[ParsedIncome] = Field(default_factory=list)
    positions: list[ParsedPosition] = Field(default_factory=list)
    warnings: list[RowWarning] = Field(default_factory=list)
