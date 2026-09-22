"""Informes de fundos imobiliários (CVM).

Vacância e imóveis só existem quando o fundo informa — por isso quase tudo é opcional
e a página mostra "—" com o motivo, nunca zero (§3.5).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import Money, Price, Quantity, Ratio, UpdatedAt


class FiiReport(Base):
    __tablename__ = "fii_reports"
    __table_args__ = (Index("ix_fii_reports_period", "period"),)

    ticker: Mapped[str] = mapped_column(
        String(20), ForeignKey("securities.ticker", ondelete="CASCADE"), primary_key=True
    )
    #: Primeiro dia do mês de referência do informe.
    period: Mapped[date] = mapped_column(Date, primary_key=True)

    #: Patrimônio líquido do fundo e o mesmo valor por cota (base do P/VP).
    nav: Mapped[Money | None]
    nav_per_share: Mapped[Price | None]
    shares: Mapped[Quantity | None]
    shareholders: Mapped[int | None] = mapped_column(Integer)
    #: Rendimento distribuído por cota no mês.
    income_per_share: Mapped[Price | None]
    vacancy_physical: Mapped[Ratio | None]
    vacancy_financial: Mapped[Ratio | None]
    admin_fee: Mapped[Ratio | None]
    manager: Mapped[str | None] = mapped_column(String(200))
    administrator: Mapped[str | None] = mapped_column(String(200))
    #: Tijolo, papel, híbrido, FoF — alimenta o filtro de `/fiis` e `/setores`.
    segment: Mapped[str | None] = mapped_column(String(60))
    document_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[UpdatedAt]
