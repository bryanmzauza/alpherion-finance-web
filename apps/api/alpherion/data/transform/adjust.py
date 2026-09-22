"""Fator de ajuste do histórico de preços por proventos e eventos.

Sem ajuste, o gráfico de qualquer papel que pagou dividendo ou desdobrou mostra quedas
que nunca existiram: um desdobramento 1:2 vira −50% na tela e a rentabilidade histórica
sai errada — inclusive a do raio-x da carteira, que lê a mesma coluna.

Como funciona: cada evento tem um **fator**, e o preço de um dia é multiplicado pelo
produto dos fatores de **todos os eventos posteriores** a ele. O último dia fica com
fator 1 (nada aconteceu depois), e a série inteira passa a ser comparável com o preço
de hoje — é a convenção de "ajuste retroativo" que o mercado usa.

Os fatores:

- **Dividendo, JCP ou rendimento** de R$ V, com fechamento `cum` de R$ P: `(P − V) / P`
  — o preço cai pelo valor distribuído no dia ex.
- **Desdobramento 1:N** (uma ação vira N): `1 / N` — o preço divide por N.
- **Grupamento N:1** (N ações viram uma): `N` — o preço multiplica por N.
- **Bonificação de X%**: `1 / (1 + X/100)` — o acionista recebe ações novas.
- **Subscrição**: nenhum — é direito, não distribuição, e não ajusta preço.

O preço `cum` é o fechamento do **último pregão antes da data ex** — o último dia em que
o papel ainda valia o provento. Sem ele (série começa depois, ou pregão faltando), o
evento é ignorado com aviso: ajustar por um preço errado é pior do que não ajustar.
"""

from __future__ import annotations

import logging
from bisect import bisect_left
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Final

logger = logging.getLogger(__name__)

ONE: Final = Decimal(1)
ZERO: Final = Decimal(0)

#: Eventos que distribuem caixa — ajustam pelo valor sobre o preço `cum`.
CASH_KINDS: Final = frozenset({"dividend", "jcp", "fii_income"})
#: Eventos que mudam a quantidade de ações — ajustam pela proporção.
RATIO_KINDS: Final = frozenset({"split", "reverse_split", "bonus"})


@dataclass(frozen=True, slots=True)
class Event:
    """Um evento corporativo que afeta o preço, como vem de `corporate_actions`."""

    ex_date: date
    kind: str
    value_per_share: Decimal | None = None
    #: Desdobramento/grupamento: "1:2" (antigas:novas). Bonificação: "10%".
    ratio: str | None = None


@dataclass(frozen=True, slots=True)
class AdjustedQuote:
    date: date
    close: Decimal
    adj_factor: Decimal
    close_adjusted: Decimal


def parse_ratio(raw: str | None) -> Decimal | None:
    """`"1:2"` → 2 (cada ação vira 2); `"10%"` → `Decimal("0.10")`.

    Devolve a **proporção**, não o fator: quem traduz proporção em fator é
    `event_factor`, porque o sentido muda entre desdobramento e grupamento.
    """
    if not raw:
        return None
    text = raw.strip().replace(",", ".")
    try:
        if text.endswith("%"):
            return Decimal(text[:-1]) / Decimal(100)
        if ":" in text:
            left, right = text.split(":", 1)
            old, new = Decimal(left), Decimal(right)
            if old <= ZERO or new <= ZERO:
                return None
            return new / old
        return Decimal(text)
    except (InvalidOperation, ValueError):
        logger.warning("proporção de evento não reconhecida: %r", raw)
        return None


def event_factor(event: Event, cum_close: Decimal | None) -> Decimal | None:
    """Fator de um evento. `None` = não dá para ajustar (e o evento é ignorado)."""
    if event.kind in CASH_KINDS:
        if event.value_per_share is None or cum_close is None or cum_close <= ZERO:
            return None
        if event.value_per_share >= cum_close:
            # Distribuição maior que o preço acontece (redução de capital, FII em
            # liquidação) e um fator ≤ 0 inverteria a série inteira.
            logger.warning(
                "provento de %s em %s (R$ %s) ≥ fechamento cum (R$ %s): evento ignorado",
                event.kind,
                event.ex_date,
                event.value_per_share,
                cum_close,
            )
            return None
        return (cum_close - event.value_per_share) / cum_close

    if event.kind not in RATIO_KINDS:
        return None  # subscrição e o que mais vier: não mexe no preço

    proportion = parse_ratio(event.ratio)
    if proportion is None or proportion <= ZERO:
        return None
    if event.kind == "bonus":
        return ONE / (ONE + proportion)  # X% de ações novas para cada ação antiga

    # Desdobramento e grupamento são a mesma conta na convenção "antigas:novas":
    # 1:2 dá proporção 2 (o preço divide por 2); 10:1 dá 0,1 (o preço multiplica por 10).
    if (event.kind == "split" and proportion < ONE) or (
        event.kind == "reverse_split" and proportion > ONE
    ):
        # Proporção no sentido contrário ao do evento: a fonte escreveu invertido. Não
        # "corrigimos" — aplicar o inverso em silêncio esconderia um dado errado.
        logger.warning(
            "%s em %s com proporção %s: sentido contrário ao do evento, conferir a fonte",
            event.kind,
            event.ex_date,
            event.ratio,
        )
    return ONE / proportion


def _cum_close(dates: Sequence[date], closes: Sequence[Decimal], ex_date: date) -> Decimal | None:
    """Fechamento do último pregão **antes** da data ex."""
    position = bisect_left(dates, ex_date)
    return closes[position - 1] if position > 0 else None


def adjust(
    quotes: Sequence[tuple[date, Decimal]],
    events: Iterable[Event],
) -> list[AdjustedQuote]:
    """Aplica o ajuste retroativo a uma série de fechamentos ordenada por data.

    Devolve a série com o fator acumulado e o fechamento ajustado de cada dia. O último
    dia sempre tem fator 1: o ajuste é relativo ao preço de hoje, e é isso que faz o
    gráfico de 5 anos ser comparável com a cotação do cabeçalho.
    """
    if not quotes:
        return []
    ordered = sorted(quotes, key=lambda item: item[0])
    dates = [item[0] for item in ordered]
    closes = [item[1] for item in ordered]

    factors: list[tuple[date, Decimal]] = []
    for event in sorted(events, key=lambda e: e.ex_date):
        if event.ex_date <= dates[0] or event.ex_date > dates[-1]:
            continue  # fora da série: não há preço anterior para ajustar
        factor = event_factor(event, _cum_close(dates, closes, event.ex_date))
        if factor is not None:
            factors.append((event.ex_date, factor))

    # Varre de trás para frente acumulando: o fator de um dia é o produto dos eventos
    # que vieram depois dele.
    accumulated = ONE
    adjusted: list[AdjustedQuote] = []
    pending = list(reversed(factors))
    for day, close in zip(reversed(dates), reversed(closes), strict=True):
        while pending and pending[0][0] > day:
            accumulated *= pending.pop(0)[1]
        adjusted.append(
            AdjustedQuote(
                date=day,
                close=close,
                adj_factor=accumulated,
                close_adjusted=close * accumulated,
            )
        )
    adjusted.reverse()
    return adjusted
