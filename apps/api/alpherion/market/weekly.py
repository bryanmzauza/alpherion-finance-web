"""Números da Leitura de Mercado (site.md §2.3, ferramenta `leitura-semanal.py`).

Porte da ferramenta que gera os números do vídeo de segunda-feira. Duas diferenças em
relação ao script original, e as duas são deliberadas:

- **A fonte é o nosso banco, não o Yahoo.** O script de vídeo lê `mercado.py` (Yahoo),
  que está fora do produto por falta de termos de uso (ADR 5). Aqui as séries vêm de
  `daily_quotes`, `index_daily`, `crypto_daily` e `macro_series` — as mesmas tabelas que
  alimentam as páginas públicas. É o que garante que o número do vídeo e o número do
  site sejam o mesmo número, que é a razão de existir deste endpoint.
- **A matemática é explícita.** Correlação de Pearson e desvio-padrão amostral escritos
  à mão, em vez de `pandas`: são quinze linhas, dão o mesmo resultado que
  `.corr()`/`.std()` (que usa `ddof=1`) e deixam visível o que está sendo calculado —
  inclusive a anualização, que usa 365 dias para cripto (negocia todo dia) e 252 para
  bolsa (só pregões). Trocar esse fator é o erro mais fácil de cometer aqui, e o mais
  difícil de perceber: a volatilidade sai ~20% errada e continua parecendo plausível.

Nada aqui é recomendação: é descrição do que aconteceu, com data e fonte (§8.3).
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

#: Dias por ano para anualizar a volatilidade, por natureza do ativo.
TRADING_DAYS_STOCK: Final = 252
TRADING_DAYS_CRYPTO: Final = 365

#: Janelas do radar de risco, em pregões.
WINDOWS: Final = (30, 90, 252)

#: Mínimo de pontos para um número fazer sentido. Correlação de 3 dias é ruído com
#: aparência de fato — e o vídeo mostraria isso como se fosse informação.
MIN_POINTS: Final = 10


@dataclass(frozen=True, slots=True)
class Series:
    """Uma série de fechamentos, ordenada por data."""

    key: str
    label: str
    points: list[tuple[dt.date, Decimal]]
    #: Cripto negocia todo dia; bolsa, só em pregão. Muda a anualização.
    crypto: bool = False

    def value_at(self, day: dt.date) -> Decimal | None:
        """Último fechamento até `day` — o "as of" do script original."""
        candidates = [value for date_, value in self.points if date_ <= day]
        return candidates[-1] if candidates else None

    def returns(self, *, until: dt.date, window: int) -> list[float]:
        """Retornos diários das últimas `window` observações até `until`."""
        values = [float(v) for d, v in self.points if d <= until and v > 0]
        if len(values) < 2:
            return []
        daily = [values[i] / values[i - 1] - 1 for i in range(1, len(values))]
        return daily[-window:]


@dataclass(frozen=True, slots=True)
class Change:
    key: str
    label: str
    price: Decimal | None
    change_7d: float | None
    change_30d: float | None
    change_ytd: float | None
    missing_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Correlation:
    pair: tuple[str, str]
    windows: dict[int, float | None]


@dataclass(frozen=True, slots=True)
class Volatility:
    key: str
    windows: dict[int, float | None]


def pct_change(current: Decimal | None, previous: Decimal | None) -> float | None:
    """Variação entre dois fechamentos. Sem um dos dois, `None` — nunca zero."""
    if current is None or previous is None or previous == 0:
        return None
    return float(current / previous - 1)


def correlation(a: list[float], b: list[float]) -> float | None:
    """Pearson sobre os retornos pareados. Mesmo resultado de `pandas.Series.corr`."""
    size = min(len(a), len(b))
    if size < MIN_POINTS:
        return None
    x, y = a[-size:], b[-size:]
    mean_x, mean_y = sum(x) / size, sum(y) / size
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=True))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)
    if var_x <= 0 or var_y <= 0:
        return None
    return cov / math.sqrt(var_x * var_y)


def volatility(returns: list[float], *, crypto: bool) -> float | None:
    """Desvio-padrão amostral anualizado. `ddof=1`, como o `pandas.std()` padrão."""
    if len(returns) < MIN_POINTS:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    days = TRADING_DAYS_CRYPTO if crypto else TRADING_DAYS_STOCK
    return math.sqrt(variance) * math.sqrt(days)


def snapshot(series: list[Series], *, reference: dt.date) -> list[Change]:
    """Preço e variações de 7 dias, 30 dias e no ano."""
    week = reference - dt.timedelta(days=7)
    month = reference - dt.timedelta(days=30)
    year_start = dt.date(reference.year - 1, 12, 31)

    changes: list[Change] = []
    for item in series:
        price = item.value_at(reference)
        changes.append(
            Change(
                key=item.key,
                label=item.label,
                price=price,
                change_7d=pct_change(price, item.value_at(week)),
                change_30d=pct_change(price, item.value_at(month)),
                change_ytd=pct_change(price, item.value_at(year_start)),
                missing_reason=None if price is not None else "série sem dado na data",
            )
        )
    return changes


def correlations(
    series: dict[str, Series],
    pairs: list[tuple[str, str]],
    *,
    reference: dt.date,
) -> list[Correlation]:
    result: list[Correlation] = []
    for left, right in pairs:
        a, b = series.get(left), series.get(right)
        windows: dict[int, float | None] = {}
        for window in WINDOWS:
            windows[window] = (
                correlation(
                    a.returns(until=reference, window=window),
                    b.returns(until=reference, window=window),
                )
                if a and b
                else None
            )
        result.append(Correlation(pair=(left, right), windows=windows))
    return result


def volatilities(series: list[Series], *, reference: dt.date) -> list[Volatility]:
    return [
        Volatility(
            key=item.key,
            windows={
                window: volatility(item.returns(until=reference, window=window), crypto=item.crypto)
                for window in WINDOWS
            },
        )
        for item in series
    ]


def extremes(
    item: Series, *, reference: dt.date, days: int = 365
) -> tuple[Decimal | None, Decimal | None]:
    """Mínimo e máximo da janela — os "52 semanas" do roteiro."""
    start = reference - dt.timedelta(days=days)
    values = [v for d, v in item.points if start <= d <= reference]
    return (min(values), max(values)) if values else (None, None)
