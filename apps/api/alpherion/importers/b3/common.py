"""Peças comuns aos três arquivos da Área do Investidor."""

from __future__ import annotations

from typing import Any

from alpherion.importers.assets import AssetHint
from alpherion.importers.models import AssetClass, IncomeKind
from alpherion.importers.tabular import norm, parse_ticker

#: Como a B3 escreve o tipo de provento → `income_kind`. Chave já normalizada.
INCOME_KINDS: dict[str, IncomeKind] = {
    "dividendo": "dividend",
    "dividendos": "dividend",
    "juros sobre capital proprio": "jcp",
    "jcp": "jcp",
    "rendimento": "fii_income",
    "rendimentos": "fii_income",
    "juros": "interest",
}


def product_hint(product: Any, class_hint: AssetClass | None = None) -> AssetHint | None:
    """`PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS` → dica de ticker; `Tesouro Selic 2029`
    → dica de título. Texto que não é nem um nem outro → `None` (linha ignorada)."""
    text = str(product or "").strip()
    if not text:
        return None
    if norm(text).startswith("tesouro") or class_hint == "treasury":
        return AssetHint(kind="treasury", code=text)
    ticker = parse_ticker(text)
    if ticker is None:
        return None
    name = text.split(" - ", 1)[1].strip() if " - " in text else None
    return AssetHint(kind="ticker", code=ticker, name=name, class_hint=class_hint)
