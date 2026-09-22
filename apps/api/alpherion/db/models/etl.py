"""Controle do pipeline: execuções dos jobs e registro das fontes com seus termos.

`data_sources` é bloqueante por decisão do ADR-017: em produção, job de fonte sem
`terms_checked_at` não roda. `etl_runs` é a base do alerta de frescor (§3.6 do plano)
e do agendamento idempotente (um job não roda duas vezes para o mesmo período).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from alpherion.db.base import Base
from alpherion.db.types import ETL_STATUSES, CreatedAt, UpdatedAt, enum_check


class EtlRun(Base):
    """Uma execução de um job, por período.

    `period` é a "unidade de trabalho" (o dia do pregão, o mês do informe, o ano da DFP):
    é o que torna o job idempotente e o reprocessamento previsível.
    """

    __tablename__ = "etl_runs"
    __table_args__ = (
        enum_check("status", ETL_STATUSES, name="status_valido"),
        Index("ix_etl_runs_job_started", "job", "started_at"),
        Index("ix_etl_runs_job_period", "job", "period"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job: Mapped[str] = mapped_column(String(60))
    period: Mapped[date | None] = mapped_column(Date)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12))
    rows: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]


class DataSource(Base):
    """Fonte de dados e o estado da verificação de termos (site.md §8.10).

    `terms_checked_at` vazio = fonte não liberada para produção (ADR-017).
    `attribution` é o texto que o `SourceBadge` mostra na página.
    """

    __tablename__ = "data_sources"

    source: Mapped[str] = mapped_column(String(40), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    #: Resumo do que a licença permite, com o documento de referência.
    license_note: Mapped[str | None] = mapped_column(Text)
    #: "Fonte: CVM", "Dados por CoinGecko" — usado pelo SourceBadge.
    attribution: Mapped[str] = mapped_column(String(120))
    terms_checked_at: Mapped[date | None] = mapped_column(Date)
    last_loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[UpdatedAt]
