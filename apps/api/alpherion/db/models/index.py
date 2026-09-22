"""Índices da B3 (Ibovespa, IFIX, IDIV, SMLL, IBrX 100…) e suas carteiras teóricas.

A carteira teórica muda a cada quadrimestre e é publicada com prévias; por isso a
composição é guardada **por data de carga** e a página sempre mostra a data ao lado.

ADR-017: índices são propriedade intelectual da B3 (os termos do site são explícitos).
Tudo aqui fica atrás de `MARKET_B3_PRICES_ENABLED`.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import Money, Quantity, Ratio, Slug, Ticker, UpdatedAt


class MarketIndex(Base):
    __tablename__ = "indices"

    slug: Mapped[Slug] = mapped_column(primary_key=True)
    #: Código na B3 (IBOV, IFIX, IDIV…).
    b3_code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    #: Quando a carteira é reavaliada ("quadrimestral: jan, mai, set").
    rebalance_note: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[UpdatedAt]


class IndexDaily(Base):
    __tablename__ = "index_daily"
    __table_args__ = (Index("ix_index_daily_date", "date"),)

    slug: Mapped[str] = mapped_column(
        String(80), ForeignKey("indices.slug", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[Money]
    change_pct: Mapped[Ratio | None]
    updated_at: Mapped[UpdatedAt]


class IndexComposition(Base):
    __tablename__ = "index_compositions"
    __table_args__ = (Index("ix_index_compositions_ticker", "ticker"),)

    slug: Mapped[str] = mapped_column(
        String(80), ForeignKey("indices.slug", ondelete="CASCADE"), primary_key=True
    )
    #: Data da carteira vigente (não a data da consulta).
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[Ticker] = mapped_column(primary_key=True)
    #: Participação no índice (0–1).
    weight: Mapped[Ratio | None]
    theoretical_qty: Mapped[Quantity | None]
    updated_at: Mapped[UpdatedAt]
