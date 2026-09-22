"""Séries macro do BCB (SGS): Selic, CDI, IPCA, IGP-M, PTAX.

Uma tabela só, com a série como chave: os códigos do SGS ficam documentados em
`data/sources/bcb.py`, não espalhados pelo schema. O engine usa CDI e IPCA para
comparar com a carteira; a faixa do header usa PTAX e Selic.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import MACRO_SERIES, Ratio, UpdatedAt, enum_check


class MacroSeries(Base):
    __tablename__ = "macro_series"
    __table_args__ = (
        enum_check("series", MACRO_SERIES, name="series_valida"),
        Index("ix_macro_series_date", "date"),
    )

    series: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    #: Unidade depende da série: % ao ano (selic, cdi), % no mês (ipca), R$ (ptax).
    value: Mapped[Ratio]
    updated_at: Mapped[UpdatedAt]
