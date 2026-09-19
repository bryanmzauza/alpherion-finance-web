"""base do schema market

Revision ID: 000001
Revises:
Create Date: 2026-09-19

Revisão vazia: só valida o pipeline (`market.alembic_version`).
As tabelas do §4.3 entram na Etapa 3.1.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "000001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
