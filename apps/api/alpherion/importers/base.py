"""Rascunho do parse (antes de resolver ativos) e a montagem da prévia."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from alpherion.importers.assets import AssetHint, Catalog, Resolver
from alpherion.importers.models import (
    FileKind,
    FileSummary,
    ImportPreview,
    IncomeKind,
    ParsedIncome,
    ParsedPosition,
    ParsedTransaction,
    RowRef,
    RowWarning,
)

#: Teto de avisos devolvidos: um arquivo todo errado não vira uma resposta de megabytes.
MAX_WARNINGS = 300


@dataclass(slots=True)
class DraftTransaction:
    origin: RowRef
    hint: AssetHint
    date: date
    side: Literal["buy", "sell"]
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal(0)


@dataclass(slots=True)
class DraftIncome:
    origin: RowRef
    hint: AssetHint
    date: date
    kind: IncomeKind
    net: Decimal
    gross: Decimal | None = None


@dataclass(slots=True)
class DraftPosition:
    origin: RowRef
    hint: AssetHint
    quantity: Decimal | None = None
    value_brl: Decimal | None = None
    avg_price: Decimal | None = None


@dataclass(slots=True)
class ParseResult:
    file: int
    kind: FileKind | None
    rows_in: int = 0
    rows_ok: int = 0
    transactions: list[DraftTransaction] = field(default_factory=list)
    income: list[DraftIncome] = field(default_factory=list)
    positions: list[DraftPosition] = field(default_factory=list)
    warnings: list[RowWarning] = field(default_factory=list)

    def warn(self, message: str, sheet: str | None = None, row: int | None = None) -> None:
        origin = RowRef(file=self.file, sheet=sheet, row=row) if sheet and row else None
        self.warnings.append(RowWarning(origin=origin, message=message))

    @property
    def summary(self) -> FileSummary:
        return FileSummary(
            file=self.file,
            kind=self.kind,
            rows_in=self.rows_in,
            rows_ok=self.rows_ok,
            rows_skipped=self.rows_in - self.rows_ok,
        )


def _n(value: Decimal | None) -> str:
    return "" if value is None else format(value.normalize(), "f")


async def build_preview(results: list[ParseResult], catalog: Catalog) -> ImportPreview:
    """Resolve os ativos de todos os arquivos numa consulta só e monta a prévia."""
    hints = [
        *(t.hint for r in results for t in r.transactions),
        *(i.hint for r in results for i in r.income),
        *(p.hint for r in results for p in r.positions),
    ]
    resolver = await Resolver.load(catalog, hints)
    preview = ImportPreview(files=[r.summary for r in results])

    for result in results:
        # Ocorrência contada **por arquivo**: duas linhas iguais no mesmo arquivo são dois
        # negócios; a mesma linha em dois arquivos (extratos com períodos sobrepostos) é
        # uma só, e o dedupe do `web` a descarta.
        seen: Counter[tuple[str, ...]] = Counter()
        for tx in result.transactions:
            asset = resolver.resolve(tx.hint)
            key = (asset.symbol, tx.date.isoformat(), tx.side, _n(tx.quantity), _n(tx.price))
            seen[key] += 1
            preview.transactions.append(
                ParsedTransaction(
                    origin=tx.origin,
                    asset=asset,
                    date=tx.date,
                    side=tx.side,
                    quantity=tx.quantity,
                    price=tx.price,
                    fees=tx.fees,
                    occurrence=seen[key],
                )
            )
        for inc in result.income:
            asset = resolver.resolve(inc.hint)
            income_key = (asset.symbol, inc.date.isoformat(), inc.kind, _n(inc.gross), _n(inc.net))
            seen[income_key] += 1
            preview.income.append(
                ParsedIncome(
                    origin=inc.origin,
                    asset=asset,
                    date=inc.date,
                    kind=inc.kind,
                    gross=inc.gross,
                    net=inc.net,
                    occurrence=seen[income_key],
                )
            )
        for pos in result.positions:
            preview.positions.append(
                ParsedPosition(
                    origin=pos.origin,
                    asset=resolver.resolve(pos.hint),
                    quantity=pos.quantity,
                    value_brl=pos.value_brl,
                    avg_price=pos.avg_price,
                )
            )
        preview.warnings.extend(result.warnings)

    preview.warnings.extend(RowWarning(message=m) for m in resolver.warnings.values())
    preview.positions = _merge_positions(preview.positions)
    if len(preview.warnings) > MAX_WARNINGS:
        extra = len(preview.warnings) - MAX_WARNINGS
        preview.warnings = [
            *preview.warnings[:MAX_WARNINGS],
            RowWarning(message=f"mais {extra} avisos omitidos"),
        ]
    return preview


def _merge_positions(positions: list[ParsedPosition]) -> list[ParsedPosition]:
    """O mesmo ativo em duas corretoras (ou duas abas) vira uma posição só, somada."""
    merged: dict[tuple[str, str], ParsedPosition] = {}
    for pos in positions:
        key = (pos.asset.asset_class, pos.asset.symbol)
        current = merged.get(key)
        if current is None:
            merged[key] = pos.model_copy()
            continue
        a, b = _cost(current), _cost(pos)
        cost = a + b if a is not None and b is not None else None
        quantity = _add(current.quantity, pos.quantity)
        merged[key] = current.model_copy(
            update={
                "quantity": quantity,
                "value_brl": _add(current.value_brl, pos.value_brl),
                "avg_price": (cost / quantity).quantize(Decimal("0.000001"))
                if cost is not None and quantity
                else None,
            }
        )
    return list(merged.values())


def _add(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None:
        return a if b is None else b
    return a + b


def _cost(pos: ParsedPosition) -> Decimal | None:
    if pos.quantity is None or pos.avg_price is None:
        return None
    return pos.quantity * pos.avg_price
