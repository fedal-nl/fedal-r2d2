"""Scope vocabulary uniqueness to its owning user.

Revision ID: a41f8c7d2e90
Revises: 3e2f8a9c1d44
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a41f8c7d2e90"
down_revision: str | Sequence[str] | None = "3e2f8a9c1d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow each user to own an independent copy of a vocabulary term."""
    op.drop_constraint(
        "uq_vocabulary_text_language",
        "vocabulary",
        schema="spanglish",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_vocabulary_text_language_user",
        "vocabulary",
        ["text", "language_id", "user_id"],
        schema="spanglish",
    )


def downgrade() -> None:
    """Restore global vocabulary uniqueness."""
    op.drop_constraint(
        "uq_vocabulary_text_language_user",
        "vocabulary",
        schema="spanglish",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_vocabulary_text_language",
        "vocabulary",
        ["text", "language_id"],
        schema="spanglish",
    )
