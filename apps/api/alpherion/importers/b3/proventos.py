"""Proventos recebidos, de dois relatórios da Área do Investidor.

- **Movimentação** (Extratos → Movimentação): `Entrada/Saída · Data · Movimentação ·
  Produto · Instituição · Quantidade · Preço unitário · Valor da Operação`. Só as linhas
  de **crédito** cujo tipo é provento (dividendo, JCP, rendimento, juros) entram; o resto
  — liquidação de negócio, transferência, desdobro, bonificação — é contado e avisado
  num aviso só, porque não é provento (a quantidade atual vem do arquivo de posição).
- **Proventos recebidos** (Eventos → Proventos): `Produto · Pagamento · Tipo de Evento ·
  Instituição · Quantidade · Preço unitário · Valor líquido`.

Os dois trazem o valor **líquido** (JCP já sem o IR), então `gross` fica vazio. Enviar
os dois relatórios juntos não duplica: a mesma linha gera a mesma chave de dedupe.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from alpherion.importers.b3.common import INCOME_KINDS, product_hint
from alpherion.importers.base import DraftIncome, ParseResult
from alpherion.importers.models import RowRef
from alpherion.importers.tabular import Sheet, Table, find_table, norm, parse_date, parse_decimal

MOVIMENTACAO = {
    "direction": ("Entrada/Saída", "Entrada/Saida"),
    "date": ("Data",),
    "event": ("Movimentação", "Movimentacao"),
    "product": ("Produto",),
}
MOVIMENTACAO_OPTIONAL = {"value": ("Valor da Operação", "Valor da Operacao", "Valor")}

RECEBIDOS = {
    "product": ("Produto",),
    "date": ("Pagamento", "Data de Pagamento", "Data do Pagamento"),
    "event": ("Tipo de Evento", "Tipo", "Evento"),
    "value": ("Valor líquido", "Valor Liquido", "Valor"),
}


def find(sheet: Sheet) -> Table | None:
    return find_table(sheet, MOVIMENTACAO, MOVIMENTACAO_OPTIONAL) or find_table(sheet, RECEBIDOS)


def parse(table: Table, sheet: Sheet, result: ParseResult, today: date) -> None:
    is_statement = "direction" in table.columns
    ignored: Counter[str] = Counter()

    for row, record in table.records():
        result.rows_in += 1
        if is_statement and not norm(record["direction"]).startswith("credito"):
            ignored[str(record.get("event") or "débito")] += 1
            continue
        event = norm(record["event"])
        kind = INCOME_KINDS.get(event)
        if kind is None:
            # "Dividendo - Transferido" e afins: provento movido entre corretoras, não pago.
            ignored[str(record.get("event") or "sem tipo")] += 1
            continue
        hint = product_hint(record["product"])
        if hint is None:
            result.warn("produto sem código de negociação reconhecível", sheet.name, row)
            continue
        when = parse_date(record["date"])
        if when is None or when > today:
            result.warn(
                "data de pagamento inválida ou futura (provento provisionado?)", sheet.name, row
            )
            continue
        value = parse_decimal(record.get("value"))
        if value is None or value <= 0:
            result.warn("provento sem valor", sheet.name, row)
            continue
        if kind == "fii_income" and hint.kind == "treasury":
            kind = "interest"
        result.income.append(
            DraftIncome(
                origin=RowRef(file=result.file, sheet=sheet.name, row=row),
                hint=hint,
                date=when,
                kind=kind,
                net=value,
            )
        )
        result.rows_ok += 1

    if ignored:
        total = sum(ignored.values())
        tipos = ", ".join(f"{name} ({n})" for name, n in ignored.most_common(6))
        result.warn(f"{total} linhas que não são proventos pagos foram ignoradas: {tipos}")
