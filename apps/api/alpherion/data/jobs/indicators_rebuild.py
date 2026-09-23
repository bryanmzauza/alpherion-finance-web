"""Recalcula `indicators_daily` a partir do que já está no banco.

Roda por último, depois de demonstrações, cotações, eventos e informes. Não baixa nada:
lê `financial_statements`, `company_facts`, `daily_quotes`, `corporate_actions` e
`fii_reports` e aplica `transform/indicators.py`.

Duas coisas que este job garante e que a página depende:

- **Motivo junto com a ausência.** Cada indicador `null` grava por que ficou `null`
  (`missing_reasons`), e é isso que vira o tooltip do "—". Indicador sumido sem
  explicação é o que faz o leitor desconfiar do número ao lado.
- **Sem preço, o resto sai.** Com `MARKET_B3_PRICES_ENABLED=false` (ADR-017) não há
  cotação, e os indicadores de balanço — ROE, ROIC, margens, endividamento — continuam
  sendo calculados e publicados.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from alpherion.data.jobs import base
from alpherion.data.transform import cvm_accounts, indicators
from alpherion.data.transform.cvm_statements import ANNUAL, StatementRow
from alpherion.db.models import (
    CompanyFact,
    CorporateAction,
    DailyQuote,
    FiiReport,
    FinancialStatement,
    IndicatorDaily,
    Security,
)
from alpherion.db.upsert import upsert

logger = logging.getLogger(__name__)

JOB = "indicators_rebuild"
#: Proventos que entram no DY e no payout — os que viram caixa para o investidor.
CASH_KINDS = ("dividend", "jcp", "fii_income")


def run(*, reference: date | None = None, tickers: list[str] | None = None) -> None:
    """Recalcula os indicadores **na data do último pregão carregado**.

    A data é a do fechamento que entra no P/L, não a do calendário: rodando num sábado,
    ou na manhã seguinte, o indicador continua sendo "no fechamento de sexta". É também
    a data que as listas usam para juntar cotação e indicador — com a data do calendário
    as duas não se encontravam e a tabela saía sem P/L nem DY.
    """
    with base.run(JOB, period=reference or date.today()) as ctx:
        today = reference or _last_trading_day(ctx) or date.today()
        alvos = _tickers(ctx, only=tickers)
        rows = []
        for ticker, cvm_code, kind in alvos:
            computed = _for_ticker(ctx, ticker=ticker, cvm_code=cvm_code, kind=kind, today=today)
            if computed is None:
                continue
            values, missing, inputs = computed
            rows.append(
                {
                    "ticker": ticker,
                    "date": today,
                    **{name: value for name, value in values.items()},
                    "inputs": inputs,
                    "missing_reasons": missing,
                }
            )
        ctx.wrote(upsert(ctx.session, IndicatorDaily, rows))


def _tickers(
    ctx: base.JobContext, *, only: list[str] | None = None
) -> list[tuple[str, int | None, str]]:
    """Papéis a recalcular: (ticker, código CVM, classe). `only` limita o reprocessamento."""
    statement = select(Security.ticker, Security.cvm_code, Security.type).where(
        Security.status == "active"
    )
    if only:
        statement = statement.where(Security.ticker.in_(only))
    rows = ctx.session.execute(statement.order_by(Security.ticker)).all()
    return [(str(row[0]), row[1], str(row[2])) for row in rows]


def _for_ticker(
    ctx: base.JobContext,
    *,
    ticker: str,
    cvm_code: int | None,
    kind: str,
    today: date,
) -> tuple[dict[str, Decimal | None], dict[str, str], dict[str, object]] | None:
    price = _last_close(ctx, ticker)
    dividends = _dividends_12m(ctx, ticker, today)

    if kind in ("fii", "fiagro"):
        report = _last_fii_report(ctx, ticker)
        fundamentals = cvm_accounts.Fundamentals(
            cvm_code=cvm_code or 0,
            period_end=report[0] if report else today,
            period_type=ANNUAL,
            consolidated=True,
        )
        result = indicators.compute(
            fundamentals,
            price=price,
            dividends_12m_per_share=dividends,
            nav_per_share=report[1] if report else None,
        )
        return result.values, result.missing, result.inputs

    if cvm_code is None:
        return None  # ETF e BDR não têm demonstração própria: indicador vem no v1.x

    statements = _statements(ctx, cvm_code)
    period = cvm_accounts.latest_period(statements, consolidated=True)
    consolidated = period is not None
    if period is None:
        period = cvm_accounts.latest_period(statements, consolidated=False)
    if period is None:
        return None

    fundamentals = cvm_accounts.extract(
        statements,
        cvm_code=cvm_code,
        period_end=period,
        period_type=ANNUAL,
        consolidated=consolidated,
    )
    result = indicators.compute(
        fundamentals,
        price=price,
        shares=_shares(ctx, cvm_code),
        dividends_12m_per_share=dividends,
    )
    return result.values, result.missing, result.inputs


def _statements(ctx: base.JobContext, cvm_code: int) -> list[StatementRow]:
    rows = ctx.session.execute(
        select(
            FinancialStatement.period_end,
            FinancialStatement.period_type,
            FinancialStatement.statement,
            FinancialStatement.consolidated,
            FinancialStatement.account_code,
            FinancialStatement.account_name,
            FinancialStatement.value,
            FinancialStatement.version,
        ).where(
            FinancialStatement.cvm_code == cvm_code,
            FinancialStatement.period_type == ANNUAL,
        )
    )
    return [
        StatementRow(
            cvm_code=cvm_code,
            period_end=period_end,
            period_type=period_type,
            statement=statement,
            consolidated=consolidated,
            account_code=account_code,
            account_name=account_name,
            value=Decimal(str(value)) if value is not None else None,
            version=version,
            period_start=None,
        )
        for (
            period_end,
            period_type,
            statement,
            consolidated,
            account_code,
            account_name,
            value,
            version,
        ) in rows
    ]


def _last_trading_day(ctx: base.JobContext) -> date | None:
    return ctx.session.execute(select(func.max(DailyQuote.date))).scalar()


def _last_close(ctx: base.JobContext, ticker: str) -> Decimal | None:
    value = ctx.session.execute(
        select(DailyQuote.close)
        .where(DailyQuote.ticker == ticker)
        .order_by(DailyQuote.date.desc())
        .limit(1)
    ).scalar()
    return Decimal(str(value)) if value is not None else None


def _shares(ctx: base.JobContext, cvm_code: int) -> Decimal | None:
    value = ctx.session.execute(
        select(CompanyFact.shares_outstanding)
        .where(CompanyFact.cvm_code == cvm_code)
        .order_by(CompanyFact.reference_date.desc())
        .limit(1)
    ).scalar()
    return Decimal(str(value)) if value is not None else None


def _dividends_12m(ctx: base.JobContext, ticker: str, today: date) -> Decimal | None:
    rows = ctx.session.execute(
        select(CorporateAction.value_per_share).where(
            CorporateAction.ticker == ticker,
            CorporateAction.kind.in_(CASH_KINDS),
            CorporateAction.ex_date.is_not(None),
            CorporateAction.ex_date > today - timedelta(days=365),
            CorporateAction.ex_date <= today,
        )
    )
    return indicators.dividends_per_share_12m(
        [(Decimal(str(value)) if value is not None else None, True) for (value,) in rows]
    )


def _last_fii_report(ctx: base.JobContext, ticker: str) -> tuple[date, Decimal | None] | None:
    row = ctx.session.execute(
        select(FiiReport.period, FiiReport.nav_per_share)
        .where(FiiReport.ticker == ticker)
        .order_by(FiiReport.period.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    period, nav = row
    return period, Decimal(str(nav)) if nav is not None else None


if __name__ == "__main__":  # pragma: no cover - entrada de linha de comando
    base.main(run)
