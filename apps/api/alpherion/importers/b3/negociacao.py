"""Extrato de negociação (Área do Investidor → Extratos → Negociação).

Layout conhecido: `Data do Negócio · Tipo de Movimentação · Mercado · Prazo/Vencimento ·
Instituição · Código de Negociação · Quantidade · Preço · Valor`. Só as colunas de
`REQUIRED`/`OPTIONAL` saem da planilha — a instituição, por exemplo, não.

O arquivo **não traz taxas** (corretagem e emolumentos ficam na nota de corretagem):
as compras entram com taxa zero, e a prévia avisa. Ticker fracionário (`PETR4F`) vira o
do lote padrão. Opção, termo e futuro não são importados.
"""

from __future__ import annotations

from datetime import date

from alpherion.importers.b3.common import product_hint
from alpherion.importers.base import DraftTransaction, ParseResult
from alpherion.importers.models import RowRef
from alpherion.importers.tabular import Sheet, Table, find_table, norm, parse_date, parse_decimal

REQUIRED = {
    "date": ("Data do Negócio", "Data do Negocio", "Data da Operação", "Data do Pregão"),
    "side": ("Tipo de Movimentação", "Compra/Venda", "C/V", "Tipo"),
    "ticker": ("Código de Negociação", "Código", "Ativo", "Papel"),
    "quantity": ("Quantidade", "Qtd", "Qtde"),
    "price": ("Preço", "Preço Unitário", "Preco Medio", "Preço Médio"),
}
OPTIONAL = {"market": ("Mercado",)}

SIDES = {"compra": "buy", "c": "buy", "venda": "sell", "v": "sell"}
#: Mercados importados; o resto (opção, termo, futuro) é avisado e pulado.
SPOT_MARKETS = ("vista", "fracionario")


def find(sheet: Sheet) -> Table | None:
    return find_table(sheet, REQUIRED, OPTIONAL)


def parse(table: Table, sheet: Sheet, result: ParseResult, today: date) -> None:
    for row, record in table.records():
        result.rows_in += 1

        def skip(message: str, row: int = row) -> None:
            result.warn(message, sheet.name, row)

        market = norm(record.get("market"))
        if market and not any(m in market for m in SPOT_MARKETS):
            skip(f"mercado '{record.get('market')}' não é importado (só à vista e fracionário)")
            continue
        side = SIDES.get(norm(record["side"]))
        if side is None:
            skip("tipo de movimentação não é compra nem venda")
            continue
        hint = product_hint(record["ticker"])
        if hint is None or hint.kind != "ticker":
            skip("código de negociação inválido")
            continue
        when = parse_date(record["date"])
        if when is None or when > today:
            skip("data inválida ou no futuro")
            continue
        quantity = parse_decimal(record["quantity"])
        price = parse_decimal(record["price"])
        if quantity is None or quantity <= 0 or price is None or price < 0:
            skip("quantidade ou preço inválido")
            continue
        result.transactions.append(
            DraftTransaction(
                origin=RowRef(file=result.file, sheet=sheet.name, row=row),
                hint=hint,
                date=when,
                side="buy" if side == "buy" else "sell",
                quantity=quantity,
                price=price,
            )
        )
        result.rows_ok += 1

    if result.transactions:
        result.warn(
            "o extrato de negociação da B3 não traz taxas (corretagem, emolumentos): as "
            "compras entram sem taxa; ajuste pela nota de corretagem se quiser o custo exato"
        )
