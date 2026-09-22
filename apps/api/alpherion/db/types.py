"""Tipos e enums compartilhados pelos modelos do schema `market`.

Os enums são `VARCHAR` + CHECK, não `ENUM` nativo do Postgres: acrescentar um valor
(uma classe de ativo nova, um tipo de provento) passa a ser uma migration de constraint,
não um `ALTER TYPE` que trava a tabela.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Final

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import mapped_column

# --- vocabulários fechados (o valor guardado é sempre um destes) ---

SECURITY_TYPES: Final = ("stock", "unit", "bdr", "etf", "fii", "fiagro", "other")
MARKETS: Final = ("br", "us")  # `us` só na Fase 2, com provedor licenciado (ADR-019)
CORPORATE_ACTION_KINDS: Final = (
    "dividend",
    "jcp",
    "fii_income",
    "split",
    "reverse_split",
    "bonus",
    "subscription",
)
STATEMENT_TYPES: Final = ("dre", "bp_ativo", "bp_passivo", "dfc", "dra", "dmpl")
PERIOD_TYPES: Final = ("annual", "quarterly")
MACRO_SERIES: Final = ("selic", "selic_meta", "cdi", "ipca", "igpm", "ptax_venda", "ptax_compra")
ETL_STATUSES: Final = ("running", "success", "failed", "skipped")


def enum_check(column: str, values: tuple[str, ...], *, name: str) -> CheckConstraint:
    """CHECK com lista fechada de valores (em vez de ENUM nativo)."""
    options = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({options})", name=name)


# --- tipos numéricos, por natureza do dado ---

# Preço de ativo: 6 casas cobrem cripto em BRL e cotas de FII.
Price = Annotated[float, mapped_column(Numeric(18, 6))]
# Quantidade: cripto tem 8 casas; 10 dá folga.
Quantity = Annotated[float, mapped_column(Numeric(28, 10))]
# Valor financeiro (volume, patrimônio, receita): centavos bastam, mas a escala é grande.
Money = Annotated[float, mapped_column(Numeric(20, 2))]
# Indicador e taxa: P/L, ROE, dividend yield, participação em índice.
Ratio = Annotated[float, mapped_column(Numeric(18, 8))]

# Carimbo de atualização: sempre timestamptz preenchido pelo banco.
UpdatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
]
CreatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now()),
]

Ticker = Annotated[str, mapped_column(String(20))]
Slug = Annotated[str, mapped_column(String(80))]
