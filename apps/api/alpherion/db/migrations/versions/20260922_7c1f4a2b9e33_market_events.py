"""market_events: a agenda (site.md §4.3, ADR-018)

Revision ID: 7c1f4a2b9e33
Revises: 469ddc79c8ee
Create Date: 2026-09-22

Tabela, e não view materializada como previa o §4.3: a agenda macro vem de um
arquivo versionado (`data/content/agenda-macro.json`), e view não alcança arquivo.
Reconstruída pelo job `market_events_rebuild`, que faz rebuild por janela — um
`REFRESH MATERIALIZED VIEW` refaria a agenda inteira todo dia.

Migration **aditiva**: cria tabela nova e não toca em nada existente.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from alpherion.db.models.events import EVENT_KINDS

revision: str = "7c1f4a2b9e33"
down_revision: str | None = "469ddc79c8ee"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_events",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=True),
        sa.Column("cvm_code", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_market_events"),
        sa.CheckConstraint(
            "kind IN (" + ", ".join(f"'{kind}'" for kind in EVENT_KINDS) + ")",
            name="ck_market_events_kind_valido",
        ),
        schema="market",
    )
    # A agenda é sempre consultada por intervalo de datas (`/agenda/[ano]-[semana]`)
    # e por papel (aba Eventos da página do ativo).
    op.create_index(
        "ix_market_events_date_kind", "market_events", ["date", "kind"], schema="market"
    )
    op.create_index(
        "ix_market_events_ticker_date", "market_events", ["ticker", "date"], schema="market"
    )


def downgrade() -> None:
    op.drop_index("ix_market_events_ticker_date", table_name="market_events", schema="market")
    op.drop_index("ix_market_events_date_kind", table_name="market_events", schema="market")
    op.drop_table("market_events", schema="market")
