"""testing migration to new database

Revision ID: e065eb46edec
Revises: b51d8c9a4f20
Create Date: 2026-07-22 15:21:12.797067

This revision intentionally contains no database changes. It verifies that
Alembic can advance revisions after the public/spanglish schema split.
"""

from collections.abc import Sequence

revision: str = "e065eb46edec"
down_revision: str | Sequence[str] | None = "b51d8c9a4f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
