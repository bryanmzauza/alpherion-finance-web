"""Tesouro Direto (Tesouro Transparente, licença ODbL — `docs/fontes-de-dados.md`).

É a única fonte de preço do v1.0 que não depende de licença da B3: `/tesouro` sai
publicável mesmo com `MARKET_B3_PRICES_ENABLED=false` (ADR-017).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import Price, Ratio, Slug, UpdatedAt

INDEX_TYPES = ("selic", "ipca", "prefixado", "igpm", "renda_mais", "educa_mais", "outro")


class TreasuryBond(Base):
    """Um título do Tesouro Direto. `slug` é a URL: `/tesouro/ipca-2029`."""

    __tablename__ = "treasury_bonds"

    slug: Mapped[Slug] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    index_type: Mapped[str] = mapped_column(String(20))
    maturity: Mapped[date] = mapped_column(Date)
    #: Paga juros semestrais (afeta a leitura de fluxo, não o preço).
    coupon: Mapped[bool] = mapped_column(server_default="false")
    updated_at: Mapped[UpdatedAt]


class TreasuryDaily(Base):
    __tablename__ = "treasury_daily"
    __table_args__ = (Index("ix_treasury_daily_date", "date"),)

    slug: Mapped[str] = mapped_column(
        String(80), ForeignKey("treasury_bonds.slug", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    buy_rate: Mapped[Ratio | None]
    sell_rate: Mapped[Ratio | None]
    buy_price: Mapped[Price | None]
    sell_price: Mapped[Price | None]
    updated_at: Mapped[UpdatedAt]
