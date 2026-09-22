"""Cotações diárias (COTAHIST) — a maior tabela do schema.

**Particionada por ano** (`RANGE (date)`): são ~400 mil linhas por ano desde 1986, e
quase toda consulta é por ticker + intervalo recente. A partição do ano corrente fica
pequena o bastante para caber em cache, e reprocessar um ano é `TRUNCATE` de uma partição.

As partições são criadas na migration e pelo job `cotahist_daily` (ao virar o ano).
Ver `alpherion/db/partitions.py`.

ADR-017: nada desta tabela vai ao público sem a licença da B3 (`MARKET_B3_PRICES_ENABLED`).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import Money, Price, Quantity, Ratio, UpdatedAt


class DailyQuote(Base):
    __tablename__ = "daily_quotes"
    __table_args__ = (
        Index("ix_daily_quotes_date", "date"),
        {"postgresql_partition_by": "RANGE (date)"},
    )

    # `date` entra na PK porque o Postgres exige a chave de partição em toda constraint única.
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)

    open: Mapped[Price | None]
    high: Mapped[Price | None]
    low: Mapped[Price | None]
    close: Mapped[Price]
    #: Fechamento ajustado por proventos e eventos (calculado por `adjust_factors`).
    close_adjusted: Mapped[Price | None]
    #: Volume **financeiro** do dia (R$) — é o que mede liquidez de verdade.
    volume: Mapped[Money | None]
    #: Quantidade de papéis negociados.
    quantity: Mapped[Quantity | None]
    trades: Mapped[int | None] = mapped_column(BigInteger)
    #: Fator acumulado de ajuste; 1 quando não houve evento depois desta data.
    adj_factor: Mapped[Ratio] = mapped_column(server_default="1")
    updated_at: Mapped[UpdatedAt]
