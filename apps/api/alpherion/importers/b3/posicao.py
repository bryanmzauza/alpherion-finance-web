"""Posição consolidada (Área do Investidor → Posição → baixar), uma aba por classe.

Abas conhecidas e o que vira cada uma:

- **Ações, BDR, ETF, Fundo de Investimento**: `Produto · Instituição · Conta · Código de
  Negociação · CNPJ · Código ISIN · Tipo · Escriturador/Administrador · Quantidade ·
  Quantidade Disponível · … · Preço de Fechamento · Valor Atualizado` → quantidade.
- **Tesouro Direto**: `Produto · Instituição · Código ISIN · Indexador · Vencimento ·
  Quantidade · … · Valor Aplicado · Valor bruto · Valor líquido · Valor Atualizado` →
  quantidade de títulos e preço médio (valor aplicado ÷ quantidade).
- **Renda Fixa** (CDB, LCI, LCA, debêntures): sem cotação pública → posição **por valor**
  (valor atualizado na curva, ou MTM se a curva não vier).

A coluna **Conta** e a **Instituição** não são lidas. Linhas de total (sem produto) são
puladas. O mesmo ativo em duas corretoras é somado em `base._merge_positions`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from alpherion.importers.assets import AssetHint
from alpherion.importers.b3.common import product_hint
from alpherion.importers.base import DraftPosition, ParseResult
from alpherion.importers.models import AssetClass, RowRef
from alpherion.importers.tabular import (
    Sheet,
    Table,
    find_table,
    norm,
    parse_date,
    parse_decimal,
    parse_ticker,
)

#: Nome da aba (normalizado) → classe. Aba fora daqui é avisada e pulada.
SHEETS: dict[str, AssetClass] = {
    "acoes": "stock_br",
    "acao": "stock_br",
    "bdr": "bdr",
    "etf": "etf_br",
    "fundo de investimento": "fii",
    "fundos de investimento": "fii",
    "fii": "fii",
    "tesouro direto": "treasury",
    "renda fixa": "fixed_income",
}
#: Abas que a posição traz e o v1 não importa, avisadas pelo nome.
NOT_IMPORTED = ("opcoes", "opcao", "emprestimo", "termo", "futuro", "coe")

LISTED = {
    "product": ("Produto",),
    "ticker": ("Código de Negociação", "Codigo de Negociacao"),
    "quantity": ("Quantidade",),
}
TREASURY = {"product": ("Produto",), "quantity": ("Quantidade",)}
TREASURY_OPTIONAL = {
    "maturity": ("Vencimento",),
    "invested": ("Valor Aplicado",),
}
FIXED_INCOME = {"product": ("Produto",)}
FIXED_INCOME_OPTIONAL = {
    "code": ("Código", "Codigo"),
    "maturity": ("Vencimento",),
    "value": (
        "Valor Atualizado CURVA",
        "Valor Atualizado MTM",
        "Valor Atualizado",
        "Valor líquido",
    ),
}


def sheet_class(sheet: Sheet) -> AssetClass | None:
    return SHEETS.get(norm(sheet.name))


def is_position_file(sheets: list[Sheet]) -> bool:
    return any(sheet_class(s) is not None and find(s) is not None for s in sheets)


def find(sheet: Sheet) -> Table | None:
    cls = sheet_class(sheet)
    if cls == "treasury":
        return find_table(sheet, TREASURY, TREASURY_OPTIONAL)
    if cls == "fixed_income":
        return find_table(sheet, FIXED_INCOME, FIXED_INCOME_OPTIONAL)
    if cls is not None:
        return find_table(sheet, LISTED)
    return None


def parse_workbook(sheets: list[Sheet], result: ParseResult, today: date) -> None:
    for sheet in sheets:
        cls = sheet_class(sheet)
        if cls is None:
            name = norm(sheet.name)
            if any(n in name for n in NOT_IMPORTED):
                result.warn(f"aba '{sheet.name}' não é importada nesta versão")
            continue
        table = find(sheet)
        if table is None:
            result.warn(f"aba '{sheet.name}' sem as colunas esperadas; pulada")
            continue
        if cls == "treasury":
            _treasury(table, sheet, result)
        elif cls == "fixed_income":
            _fixed_income(table, sheet, result, today)
        else:
            _listed(table, sheet, result, cls)


def _listed(table: Table, sheet: Sheet, result: ParseResult, cls: AssetClass) -> None:
    for row, record in table.records():
        if not str(record.get("product") or "").strip():
            continue  # linha de total
        result.rows_in += 1
        ticker = parse_ticker(record["ticker"])
        quantity = parse_decimal(record["quantity"])
        if ticker is None:
            result.warn("código de negociação inválido", sheet.name, row)
            continue
        if quantity is None or quantity <= 0:
            result.warn(f"{ticker}: quantidade inválida", sheet.name, row)
            continue
        base = product_hint(record["product"], cls)
        name = base.name if base and base.kind == "ticker" else None
        result.positions.append(
            DraftPosition(
                origin=RowRef(file=result.file, sheet=sheet.name, row=row),
                hint=AssetHint(kind="ticker", code=ticker, name=name, class_hint=cls),
                quantity=quantity,
            )
        )
        result.rows_ok += 1


def _treasury(table: Table, sheet: Sheet, result: ParseResult) -> None:
    for row, record in table.records():
        product = str(record.get("product") or "").strip()
        if not product:
            continue
        result.rows_in += 1
        quantity = parse_decimal(record["quantity"])
        if quantity is None or quantity <= 0:
            result.warn(f"{product}: quantidade inválida", sheet.name, row)
            continue
        invested = parse_decimal(record.get("invested"))
        result.positions.append(
            DraftPosition(
                origin=RowRef(file=result.file, sheet=sheet.name, row=row),
                hint=AssetHint(
                    kind="treasury",
                    code=product,
                    maturity=parse_date(record.get("maturity")),
                    class_hint="treasury",
                ),
                quantity=quantity,
                avg_price=(invested / quantity).quantize(Decimal("0.000001")) if invested else None,
            )
        )
        result.rows_ok += 1


def _fixed_income(table: Table, sheet: Sheet, result: ParseResult, today: date) -> None:
    for row, record in table.records():
        product = str(record.get("product") or "").strip()
        if not product:
            continue
        result.rows_in += 1
        value = parse_decimal(record.get("value"))
        if value is None or value <= 0:
            result.warn(f"{product}: sem valor atualizado", sheet.name, row)
            continue
        maturity = parse_date(record.get("maturity"))
        if maturity is not None and maturity < today:
            result.warn(f"{product}: vencido em {maturity:%d/%m/%Y}; pulado", sheet.name, row)
            continue
        code = str(record.get("code") or "").strip()
        label = f"{product} {maturity:%m/%Y}" if maturity else product
        result.positions.append(
            DraftPosition(
                origin=RowRef(file=result.file, sheet=sheet.name, row=row),
                hint=AssetHint(kind="fixed_income", code=code or label, name=label),
                value_brl=value,
            )
        )
        result.rows_ok += 1
