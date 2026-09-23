"""CSV genérico de movimentações (modelo em `apps/web/public/csv-modelo.csv`).

Colunas: `data;tipo;ativo;quantidade;preco;taxas;classe` — as duas últimas opcionais.
Separador `;` ou `,`, número com vírgula ou ponto, data `dd/mm/aaaa` ou `aaaa-mm-dd`.

`ativo` é o ticker (`PETR4`), o nome do título (`Tesouro IPCA+ 2035`) ou o símbolo da
cripto (`BTC`). A `classe`, quando vem, desfaz a ambiguidade (`acao`, `fii`, `etf`,
`bdr`, `tesouro`, `cripto`); sem ela, o parser decide pelo formato do texto.

(O nome não é `csv.py` para não sombrear o módulo `csv` da biblioteca padrão.)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Final

from alpherion.importers.assets import AssetHint
from alpherion.importers.base import DraftTransaction, ParseResult
from alpherion.importers.models import AssetClass, RowRef
from alpherion.importers.tabular import (
    MAX_CSV_BYTES,
    ImportFileError,
    find_table,
    norm,
    parse_date,
    parse_decimal,
    parse_ticker,
    read_file,
)

MAX_LINES: Final = 1000

REQUIRED = {
    "date": ("data", "date", "data da operacao", "data do negocio"),
    "side": ("tipo", "operacao", "compra/venda", "c/v", "side"),
    "asset": ("ativo", "ticker", "codigo", "papel", "symbol", "simbolo"),
    "quantity": ("quantidade", "qtd", "qtde", "quantity"),
    "price": ("preco", "preco unitario", "price", "valor unitario"),
}
OPTIONAL = {
    "fees": ("taxas", "custos", "fees", "corretagem"),
    "asset_class": ("classe", "class", "tipo de ativo"),
}

SIDES: Final = {
    "compra": "buy",
    "c": "buy",
    "buy": "buy",
    "venda": "sell",
    "v": "sell",
    "sell": "sell",
}
CLASSES: Final[dict[str, AssetClass]] = {
    "acao": "stock_br",
    "acoes": "stock_br",
    "stock": "stock_br",
    "fii": "fii",
    "fiagro": "fii",
    "etf": "etf_br",
    "bdr": "bdr",
    "tesouro": "treasury",
    "tesouro direto": "treasury",
    "cripto": "crypto",
    "crypto": "crypto",
    "criptomoeda": "crypto",
}


def _hint(asset: str, cls: AssetClass | None) -> AssetHint | None:
    text = asset.strip()
    if not text:
        return None
    if cls == "treasury" or norm(text).startswith("tesouro"):
        return AssetHint(kind="treasury", code=text)
    if cls == "crypto":
        return AssetHint(kind="crypto", code=text.upper())
    ticker = parse_ticker(text)
    if ticker is not None:
        return AssetHint(kind="ticker", code=ticker, class_hint=cls)
    if cls is None and text.isalnum() and 2 <= len(text) <= 10:
        return AssetHint(kind="crypto", code=text.upper())
    return None


def parse_file(data: bytes, file: int, today: date) -> ParseResult:
    sheets = read_file(data, max_bytes=MAX_CSV_BYTES)
    if len(sheets) != 1 or sheets[0].name != "csv":
        raise ImportFileError("envie um arquivo CSV (para planilhas da B3, use a importação da B3)")
    sheet = sheets[0]
    if len(sheet.rows) > MAX_LINES + 1:
        raise ImportFileError(f"CSV com mais de {MAX_LINES} linhas; divida o arquivo")

    result = ParseResult(file=file, kind="csv")
    table = find_table(sheet, REQUIRED, OPTIONAL)
    if table is None:
        result.warn(
            "cabeçalho não reconhecido: a primeira linha precisa ter data, tipo, ativo, "
            "quantidade e preço (veja o modelo)"
        )
        return result

    for row, record in table.records():
        result.rows_in += 1

        def skip(message: str, row: int = row) -> None:
            result.warn(message, sheet.name, row)

        raw_class = norm(record.get("asset_class"))
        cls = CLASSES.get(raw_class) if raw_class else None
        if raw_class and cls is None:
            skip(f"classe '{record.get('asset_class')}' desconhecida")
            continue
        hint = _hint(str(record["asset"] or ""), cls)
        if hint is None:
            skip("ativo não reconhecido (use o ticker, o nome do título ou o símbolo da cripto)")
            continue
        side = SIDES.get(norm(record["side"]))
        if side is None:
            skip("tipo precisa ser compra ou venda")
            continue
        when = parse_date(record["date"])
        if when is None or when > today:
            skip("data inválida ou no futuro")
            continue
        quantity = parse_decimal(record["quantity"])
        price = parse_decimal(record["price"])
        fees = parse_decimal(record.get("fees"))
        if quantity is None or quantity <= 0 or price is None or price < 0:
            skip("quantidade ou preço inválido")
            continue
        if fees is not None and fees < 0:
            skip("taxas negativas")
            continue
        result.transactions.append(
            DraftTransaction(
                origin=RowRef(file=file, sheet=sheet.name, row=row),
                hint=hint,
                date=when,
                side="buy" if side == "buy" else "sell",
                quantity=quantity,
                price=price,
                fees=fees if fees is not None else Decimal(0),
            )
        )
        result.rows_ok += 1
    return result
