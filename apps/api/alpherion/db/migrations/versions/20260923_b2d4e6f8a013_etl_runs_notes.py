"""etl_runs.notes: as anotações de cada execução

Revision ID: b2d4e6f8a013
Revises: 7c1f4a2b9e33
Create Date: 2026-09-23

Os jobs já anotavam o que importa para entender uma execução ("papéis por tipo",
"informes sem papel listado", "meses com ISIN ambíguo", "blocos com falha") em
`JobContext.notes`, e a documentação dizia que isso ia para `etl_runs` — mas a tabela
não tinha a coluna, e as anotações se perdiam. Migration **aditiva**: coluna nova,
anulável, sem tocar em nada existente.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2d4e6f8a013"
down_revision: str | None = "7c1f4a2b9e33"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "etl_runs",
        sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="market",
    )


def downgrade() -> None:
    op.drop_column("etl_runs", "notes", schema="market")
