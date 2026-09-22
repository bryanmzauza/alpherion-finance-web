"""Fórmulas dos indicadores (site.md §3.5) — o único lugar onde eles são calculados.

Regras que valem para todos, sem exceção:

- **Indicador sem entrada fica `null`, com motivo.** Nunca zero, nunca "0,00": a página
  mostra "—" e o tooltip diz por quê ("empresa não publicou DFP 2025", "lucro 12 m
  negativo"). Zero é um número e o usuário o lê como um.
- **Denominador ≤ 0 não vira indicador.** P/L de empresa que deu prejuízo e P/VP de
  patrimônio negativo são contas que "dão certo" e enganam: o número existe e não
  significa nada. Ficam `null` com o motivo, que é informação de verdade.
- **Nenhum juízo de valor.** Aqui só sai número com fórmula pública; "caro", "barato",
  nota e preço justo não existem no produto (§8.3, ADR-018). A interpretação genérica
  fica no glossário `/indicadores`.
- **`Decimal` do começo ao fim.** Dinheiro em float dá centavo errado, e centavo errado
  numa divisão vira indicador errado na tela.

`inputs` devolve o que entrou em cada conta e `missing` o motivo de cada ausência —
os dois são gravados em `indicators_daily` para responder "de onde veio esse P/L" sem
refazer a carga. `FORMULAS_VERSION` acompanha isso: mudou fórmula, muda a versão.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Any, Final

from alpherion.data.transform.cvm_accounts import Fundamentals

logger = logging.getLogger(__name__)

#: Versão das fórmulas, gravada em `indicators_daily.inputs` (site.md §10).
FORMULAS_VERSION: Final = "1.0.0"

#: Alíquota usada no NOPAT do ROIC (IRPJ 25% + CSLL 9%). É premissa, não dado: vai em
#: `inputs` para a página poder dizer qual foi.
TAX_RATE: Final = Decimal("0.34")

ZERO: Final = Decimal(0)


@dataclass(slots=True)
class Indicators:
    """Resultado do cálculo: valores, motivos das ausências e entradas usadas."""

    values: dict[str, Decimal | None] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)

    def set(self, name: str, value: Decimal | None, *, reason: str | None = None) -> None:
        self.values[name] = value
        if value is None and reason:
            self.missing[name] = reason

    def __getitem__(self, name: str) -> Decimal | None:
        return self.values.get(name)


def divide(
    numerator: Decimal | None,
    denominator: Decimal | None,
    *,
    positive_denominator: bool = False,
) -> Decimal | None:
    """Divisão que devolve `None` em vez de explodir ou de mentir.

    `positive_denominator` é o que separa P/L (não faz sentido com prejuízo) de
    dív. líq./PL (faz sentido com dívida negativa, que é caixa líquido).
    """
    if numerator is None or denominator is None:
        return None
    if denominator == ZERO or (positive_denominator and denominator <= ZERO):
        return None
    try:
        return numerator / denominator
    except (DivisionByZero, InvalidOperation):  # pragma: no cover - guarda de segurança
        return None


def cagr(first: Decimal | None, last: Decimal | None, years: int) -> Decimal | None:
    """Crescimento anual composto entre dois pontos.

    Base negativa ou zero não tem taxa de crescimento definida — uma empresa que saiu de
    prejuízo para lucro não cresceu "300% ao ano", e publicar isso seria inventar fato.
    """
    if first is None or last is None or years <= 0:
        return None
    if first <= ZERO or last <= ZERO:
        return None
    ratio = last / first
    return Decimal(str(float(ratio) ** (1 / years) - 1))


def _reason(fundamentals: Fundamentals, *concepts: str) -> str:
    """Motivo da ausência, dito na língua da fonte ("conta 3.01 ausente na DRE")."""
    for concept in concepts:
        if concept in fundamentals.missing:
            return fundamentals.missing[concept]
    return "entrada indisponível"


def compute(
    fundamentals: Fundamentals,
    *,
    price: Decimal | None = None,
    shares: Decimal | None = None,
    dividends_12m_per_share: Decimal | None = None,
    revenue_5y_ago: Decimal | None = None,
    earnings_5y_ago: Decimal | None = None,
    nav_per_share: Decimal | None = None,
) -> Indicators:
    """Calcula todos os indicadores da página do ativo.

    `price` e `shares` são opcionais de propósito: sem a licença da B3 (ADR-017) o
    pipeline roda sem preço e os indicadores de balanço — ROE, margens, endividamento —
    saem normalmente. Os de valuation ficam `null` com o motivo, e a página mostra "—".
    """
    result = Indicators()
    revenue = fundamentals.get("revenue")
    net_income = fundamentals.get("net_income")
    equity = fundamentals.get("equity")
    ebit = fundamentals.get("ebit")
    depreciation = fundamentals.get("depreciation")
    total_assets = fundamentals.get("total_assets")
    net_debt = fundamentals.net_debt

    ebitda = ebit + depreciation if ebit is not None and depreciation is not None else None

    # --- rentabilidade e margens (não dependem de preço) ---
    result.set(
        "roe",
        divide(net_income, equity, positive_denominator=True),
        reason=(
            "patrimônio líquido negativo"
            if equity is not None and equity <= ZERO
            else _reason(fundamentals, "net_income", "equity")
        ),
    )
    result.set(
        "roa",
        divide(net_income, total_assets, positive_denominator=True),
        reason=_reason(fundamentals, "net_income", "total_assets"),
    )
    invested_capital = equity + net_debt if equity is not None and net_debt is not None else None
    nopat = ebit * (Decimal(1) - TAX_RATE) if ebit is not None else None
    result.set(
        "roic",
        divide(nopat, invested_capital, positive_denominator=True),
        reason=_reason(fundamentals, "ebit", "equity", "debt_short"),
    )
    result.set(
        "gross_margin",
        divide(fundamentals.get("gross_profit"), revenue, positive_denominator=True),
        reason=_reason(fundamentals, "gross_profit", "revenue"),
    )
    result.set(
        "ebitda_margin",
        divide(ebitda, revenue, positive_denominator=True),
        reason=(
            fundamentals.missing.get("depreciation") or _reason(fundamentals, "revenue")
            if ebitda is None
            else _reason(fundamentals, "revenue")
        ),
    )
    result.set(
        "net_margin",
        divide(net_income, revenue, positive_denominator=True),
        reason=_reason(fundamentals, "net_income", "revenue"),
    )

    # --- endividamento ---
    result.set(
        "net_debt_ebitda",
        divide(net_debt, ebitda, positive_denominator=True),
        reason=(
            fundamentals.missing.get("depreciation", "EBITDA indisponível")
            if ebitda is None
            else "EBITDA negativo"
            if ebitda <= ZERO
            else _reason(fundamentals, "debt_short", "debt_long")
        ),
    )
    result.set(
        "net_debt_equity",
        divide(net_debt, equity, positive_denominator=True),
        reason=(
            "patrimônio líquido negativo"
            if equity is not None and equity <= ZERO
            else _reason(fundamentals, "debt_short", "equity")
        ),
    )
    result.set(
        "current_ratio",
        divide(
            fundamentals.get("current_assets"),
            fundamentals.get("current_liabilities"),
            positive_denominator=True,
        ),
        reason=_reason(fundamentals, "current_assets", "current_liabilities"),
    )

    # --- por ação ---
    eps = divide(net_income, shares, positive_denominator=True)
    bvps = divide(equity, shares, positive_denominator=True)
    sem_acoes = "quantidade de ações não disponível (FCA)"
    result.set(
        "eps", eps, reason=sem_acoes if shares is None else _reason(fundamentals, "net_income")
    )
    result.set(
        "bvps", bvps, reason=sem_acoes if shares is None else _reason(fundamentals, "equity")
    )

    # --- crescimento ---
    result.set(
        "revenue_cagr_5y",
        cagr(revenue_5y_ago, revenue, 5),
        reason="sem demonstração de 5 anos atrás",
    )
    result.set(
        "earnings_cagr_5y",
        cagr(earnings_5y_ago, net_income, 5),
        reason="sem lucro positivo nos dois extremos da janela",
    )

    # --- valuation (dependem de preço; ADR-017) ---
    sem_preco = "cotação indisponível (fonte de preço não licenciada)"
    market_cap = price * shares if price is not None and shares is not None else None
    result.set("market_cap", market_cap, reason=sem_preco if price is None else sem_acoes)
    result.set(
        "pe",
        divide(price, eps, positive_denominator=True),
        reason=sem_preco
        if price is None
        else "lucro 12 m negativo"
        if eps is not None and eps <= ZERO
        else "lucro por ação indisponível",
    )
    result.set(
        "pb",
        divide(price, bvps, positive_denominator=True),
        reason=sem_preco
        if price is None
        else "patrimônio líquido negativo"
        if bvps is not None and bvps <= ZERO
        else "valor patrimonial por ação indisponível",
    )
    result.set(
        "psr",
        divide(market_cap, revenue, positive_denominator=True),
        reason=sem_preco if price is None else _reason(fundamentals, "revenue"),
    )
    enterprise_value = (
        market_cap + net_debt if market_cap is not None and net_debt is not None else None
    )
    result.set(
        "ev_ebitda",
        divide(enterprise_value, ebitda, positive_denominator=True),
        reason=sem_preco if price is None else "EBITDA indisponível ou negativo",
    )
    result.set(
        "ev_ebit",
        divide(enterprise_value, ebit, positive_denominator=True),
        reason=sem_preco if price is None else "EBIT indisponível ou negativo",
    )
    result.set(
        "dy_12m",
        divide(dividends_12m_per_share, price, positive_denominator=True),
        reason=sem_preco if price is None else "sem provento nos últimos 12 meses",
    )
    result.set(
        "payout",
        divide(dividends_12m_per_share, eps, positive_denominator=True),
        reason="lucro por ação indisponível ou negativo",
    )
    #: P/VP do FII usa o valor patrimonial da cota do informe, não o balanço.
    result.set(
        "pvp",
        divide(price, nav_per_share, positive_denominator=True),
        reason=sem_preco if price is None else "informe do fundo sem valor patrimonial da cota",
    )

    result.inputs = {
        "formulas_version": FORMULAS_VERSION,
        "period_end": fundamentals.period_end.isoformat(),
        "period_type": fundamentals.period_type,
        "consolidated": fundamentals.consolidated,
        "tax_rate": str(TAX_RATE),
        "source": "CVM",
        **{name: str(value) for name, value in fundamentals.values.items()},
        **{
            name: str(value)
            for name, value in (
                ("ebitda", ebitda),
                ("net_debt", net_debt),
                ("price", price),
                ("shares", shares),
                ("dividends_12m_per_share", dividends_12m_per_share),
            )
            if value is not None
        },
    }
    return result


def dividends_per_share_12m(
    payments: Sequence[tuple[Decimal | None, bool]],
) -> Decimal | None:
    """Soma dos proventos por ação de uma janela já filtrada (12 meses).

    Recebe pares (valor por ação, entra no cálculo) porque o que conta como provento
    depende da classe: dividendo, JCP e rendimento de FII somam; bonificação e
    subscrição, não — elas mudam a quantidade de ações, não o caixa do investidor.
    """
    values = [value for value, counts in payments if counts and value is not None]
    return sum(values, ZERO) if values else None
