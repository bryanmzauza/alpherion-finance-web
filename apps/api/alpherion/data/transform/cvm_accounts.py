"""Do formato longo da CVM para os números que as fórmulas usam.

As demonstrações chegam como uma linha por conta do **plano padronizado** da CVM, que é
estável entre companhias e entre anos — é o que torna possível calcular o mesmo
indicador para 400 empresas sem regra por empresa. O que esta camada faz é só traduzir
código de conta em conceito; a matemática fica em `indicators.py`.

Duas escolhas que valem explicação:

- **Lucro atribuído aos controladores** (3.11.01) na frente do consolidado (3.11). ROE e
  LPA de uma holding com minoritários relevantes saem inflados se usarem o consolidado;
  quando a companhia não separa, o consolidado é o que há.
- **Depreciação por nome, não por código.** É o único número aqui que a CVM não
  padroniza: cada companhia pendura a depreciação numa subconta diferente da DFC. Sem
  achá-la, o EBITDA fica `null` com motivo — melhor do que um EBITDA igual ao EBIT.
- **Instituição financeira tem outro plano de contas.** Banco não separa circulante de
  não circulante: no Itaú, "2.03" são os passivos financeiros ao custo amortizado e o
  patrimônio líquido está em "2.08"; no BB, em "2.07"; o lucro dos controladores fica
  em "3.09.01" num e "3.11.01" no outro. Por isso patrimônio e lucro são achados pelo
  **nome** da conta (com o código como reserva), e os conceitos de circulante, caixa,
  dívida e EBIT ficam ausentes **com o motivo** quando o balanço não tem "Passivo
  Circulante" — antes, o ROE do Itaú saía 1,95% e liquidez corrente de banco saía número.

Toda ausência é registrada: `Fundamentals.missing` vira o tooltip "—" da página (§3.5).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Final

from alpherion.data.transform.csv_fields import strip_accents
from alpherion.data.transform.cvm_statements import StatementRow

logger = logging.getLogger(__name__)

#: Conceito → código da conta no plano padronizado da CVM, em ordem de preferência.
ACCOUNTS: Final[dict[str, tuple[str, ...]]] = {
    # DRE
    "revenue": ("3.01",),
    "gross_profit": ("3.03",),
    "ebit": ("3.05",),  # resultado antes do resultado financeiro e dos tributos
    "net_income": ("3.11.01", "3.11", "3.09"),
    # Balanço patrimonial — ativo
    "total_assets": ("1",),
    "current_assets": ("1.01",),
    "cash": ("1.01.01",),
    "short_term_investments": ("1.01.02",),
    # Balanço patrimonial — passivo
    "current_liabilities": ("2.01",),
    "debt_short": ("2.01.04",),
    "debt_long": ("2.02.01",),
    "equity": ("2.03",),
    # DFC
    "operating_cash_flow": ("6.01",),
}

#: A conta de depreciação não tem código fixo: procuramos pelo nome dentro da DFC.
DEPRECIATION_TERMS: Final = ("depreciacao", "amortizacao", "exaustao")

#: Conceitos que só existem no plano de contas comercial (com circulante). Em banco,
#: ficam ausentes com `NOT_APPLICABLE_REASON`.
COMMERCIAL_ONLY: Final = frozenset(
    {
        "ebit",
        "current_assets",
        "cash",
        "short_term_investments",
        "current_liabilities",
        "debt_short",
        "debt_long",
    }
)
NOT_APPLICABLE_REASON: Final = (
    "não se aplica a instituição financeira (plano de contas sem circulante)"
)

#: Em que demonstração cada conceito é procurado.
STATEMENT_OF: Final[dict[str, str]] = {
    "revenue": "dre",
    "gross_profit": "dre",
    "ebit": "dre",
    "net_income": "dre",
    "total_assets": "bp_ativo",
    "current_assets": "bp_ativo",
    "cash": "bp_ativo",
    "short_term_investments": "bp_ativo",
    "current_liabilities": "bp_passivo",
    "debt_short": "bp_passivo",
    "debt_long": "bp_passivo",
    "equity": "bp_passivo",
    "operating_cash_flow": "dfc",
}


@dataclass(slots=True)
class Fundamentals:
    """Foto contábil de uma companhia num período, em reais.

    Campo `None` significa "a companhia não publicou" — e o motivo fica em `missing`.
    Nenhum campo vira zero por falta de dado: zero é um número, ausência não é.
    """

    cvm_code: int
    period_end: date
    period_type: str
    consolidated: bool
    values: dict[str, Decimal] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)

    def get(self, name: str) -> Decimal | None:
        return self.values.get(name)

    @property
    def cash_and_investments(self) -> Decimal | None:
        """Caixa + aplicações financeiras de curto prazo (base da dívida líquida)."""
        cash = self.get("cash")
        investments = self.get("short_term_investments")
        if cash is None and investments is None:
            return None
        return (cash or Decimal(0)) + (investments or Decimal(0))

    @property
    def gross_debt(self) -> Decimal | None:
        short = self.get("debt_short")
        long = self.get("debt_long")
        if short is None and long is None:
            return None
        return (short or Decimal(0)) + (long or Decimal(0))

    @property
    def net_debt(self) -> Decimal | None:
        """Dívida bruta menos caixa. Negativa é caixa líquido — e é um número válido."""
        debt = self.gross_debt
        if debt is None:
            return None
        return debt - (self.cash_and_investments or Decimal(0))


def _is_depreciation(account_name: str) -> bool:
    name = strip_accents(account_name).lower()
    return any(term in name for term in DEPRECIATION_TERMS)


def extract(
    rows: Iterable[StatementRow],
    *,
    cvm_code: int,
    period_end: date,
    period_type: str,
    consolidated: bool,
) -> Fundamentals:
    """Monta a foto contábil de um período a partir das linhas do formato longo.

    Só entram linhas do mesmo período e do mesmo escopo (consolidado ou individual):
    misturar os dois dá um ROE com lucro consolidado sobre patrimônio individual.
    """
    selected = [
        row
        for row in rows
        if row.cvm_code == cvm_code
        and row.period_end == period_end
        and row.period_type == period_type
        and row.consolidated == consolidated
    ]
    by_statement: dict[str, dict[str, StatementRow]] = {}
    for row in selected:
        by_statement.setdefault(row.statement, {})[row.account_code] = row

    result = Fundamentals(
        cvm_code=cvm_code,
        period_end=period_end,
        period_type=period_type,
        consolidated=consolidated,
    )
    financial = is_financial_layout(by_statement.get("bp_passivo", {}))
    by_name = {
        "equity": _by_name(
            by_statement.get("bp_passivo", {}), level=2, starts=("patrimonio liquido",)
        ),
        "net_income": _by_name(
            by_statement.get("dre", {}), level=3, contains=("socios da empresa controladora",)
        )
        or _by_name(by_statement.get("dre", {}), level=2, contains=("consolidado do periodo",)),
    }
    for concept, codes in ACCOUNTS.items():
        if financial and concept in COMMERCIAL_ONLY:
            result.missing[concept] = NOT_APPLICABLE_REASON
            continue
        named = by_name.get(concept)
        if named is not None and named.value is not None:
            result.values[concept] = named.value
            continue
        accounts = by_statement.get(STATEMENT_OF[concept], {})
        for code in codes:
            account = accounts.get(code)
            if account is not None and account.value is not None:
                result.values[concept] = account.value
                break
        else:
            result.missing[concept] = f"conta {codes[0]} ausente na {STATEMENT_OF[concept].upper()}"

    depreciation = _find_depreciation(by_statement.get("dfc", {}).values())
    if depreciation is not None:
        result.values["depreciation"] = depreciation
    else:
        result.missing["depreciation"] = "depreciação não identificada na DFC"
    return result


def is_financial_layout(passivo: dict[str, StatementRow]) -> bool:
    """Plano de contas de instituição financeira: 2.01 não é "Passivo Circulante"."""
    first = passivo.get("2.01")
    if first is None:
        return False
    return not _normalized(first.account_name).startswith("passivo circulante")


def _normalized(text: str) -> str:
    return " ".join(strip_accents(text).lower().replace("/", " ").split())


def _by_name(
    accounts: dict[str, StatementRow],
    *,
    level: int,
    starts: tuple[str, ...] = (),
    contains: tuple[str, ...] = (),
) -> StatementRow | None:
    """A conta de um nível do plano (2 = "2.03", 3 = "3.11.01") cujo nome casa.

    Em ordem de código, para que a escolha seja sempre a mesma.
    """
    for code in sorted(accounts):
        if code.count(".") != level - 1:
            continue
        name = _normalized(accounts[code].account_name)
        if any(name.startswith(term) for term in starts) or any(term in name for term in contains):
            return accounts[code]
    return None


def _find_depreciation(rows: Iterable[StatementRow]) -> Decimal | None:
    """Soma as subcontas de depreciação/amortização da DFC, em valor absoluto.

    Na DFC elas aparecem como ajuste ao lucro (positivas) ou como saída (negativas),
    conforme a companhia; o EBITDA soma a despesa, então o sinal não pode decidir.
    """
    total: Decimal | None = None
    for row in rows:
        if row.value is None or not _is_depreciation(row.account_name):
            continue
        total = (total or Decimal(0)) + abs(row.value)
    return total


def latest_period(rows: Iterable[StatementRow], *, consolidated: bool | None = None) -> date | None:
    """Período mais recente presente nas linhas — a DFP do ano que a companhia publicou."""
    periods = [
        row.period_end for row in rows if consolidated is None or row.consolidated == consolidated
    ]
    return max(periods) if periods else None
