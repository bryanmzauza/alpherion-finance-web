"""Indicadores calculados por ativo e por dia (`indicators_rebuild`).

Regra do site.md §3.5: indicador sem entrada disponível fica **null** e a página mostra
"—" com o motivo no tooltip — nunca zero. `inputs` guarda os valores usados no cálculo,
para responder "de onde veio esse P/L" sem refazer a conta.

ADR-017: os indicadores que dependem de preço (`price_based`) só são exibidos com a
licença da B3; os de balanço (ROE, margens, endividamento) não dependem dela.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import Money, Price, Ratio, UpdatedAt

#: Indicadores que usam preço de mercado — ficam atrás da flag da B3 (ADR-017).
PRICE_BASED = frozenset({"pe", "pb", "ev_ebitda", "ev_ebit", "psr", "dy_12m", "market_cap", "pvp"})


class IndicatorDaily(Base):
    __tablename__ = "indicators_daily"
    __table_args__ = (Index("ix_indicators_daily_date", "date"),)

    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("securities.ticker", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    # Valuation (dependem de preço)
    pe: Mapped[Ratio | None]
    pb: Mapped[Ratio | None]
    ev_ebitda: Mapped[Ratio | None]
    ev_ebit: Mapped[Ratio | None]
    psr: Mapped[Ratio | None]
    dy_12m: Mapped[Ratio | None]
    payout: Mapped[Ratio | None]
    market_cap: Mapped[Money | None]

    # Rentabilidade (só balanço)
    roe: Mapped[Ratio | None]
    roic: Mapped[Ratio | None]
    roa: Mapped[Ratio | None]
    gross_margin: Mapped[Ratio | None]
    ebitda_margin: Mapped[Ratio | None]
    net_margin: Mapped[Ratio | None]

    # Endividamento (só balanço)
    net_debt_ebitda: Mapped[Ratio | None]
    net_debt_equity: Mapped[Ratio | None]
    current_ratio: Mapped[Ratio | None]

    # Crescimento e por ação
    revenue_cagr_5y: Mapped[Ratio | None]
    earnings_cagr_5y: Mapped[Ratio | None]
    eps: Mapped[Price | None]
    bvps: Mapped[Price | None]

    # FII
    #: Preço sobre valor patrimonial da cota (o P/VP dos FIIs).
    pvp: Mapped[Ratio | None]

    #: Entradas usadas: {"lucro_12m": ..., "período": "DFP 2025", "fonte": "CVM"}.
    inputs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    #: Por que cada indicador ficou null: {"pe": "lucro negativo"} — vira tooltip.
    missing_reasons: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    updated_at: Mapped[UpdatedAt]
