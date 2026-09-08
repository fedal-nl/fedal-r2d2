"""Add local refresh sessions and require quiz ownership.

Revision ID: 3e2f8a9c1d44
Revises: c7d2e4f8a901
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3e2f8a9c1d44"
down_revision: str | Sequence[str] | None = "c7d2e4f8a901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_USER_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("client_type", sa.String(length=30), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        schema="public",
    )
    op.create_index(
        "ix_refresh_sessions_user_id",
        "refresh_sessions",
        ["user_id"],
        schema="public",
    )

    # Preserve anonymous quizzes created before authentication existed.
    op.execute(
        sa.text(
            """
            INSERT INTO public.users (id, username, is_active)
            VALUES (:id, 'legacy_anonymous', false)
            ON CONFLICT DO NOTHING
            """
        ).bindparams(id=LEGACY_USER_ID)
    )
    op.execute(
        sa.text(
            "UPDATE spanglish.quiz_sessions SET user_id = :id WHERE user_id IS NULL"
        ).bindparams(id=LEGACY_USER_ID)
    )
    op.alter_column("quiz_sessions", "user_id", nullable=False, schema="spanglish")


def downgrade() -> None:
    op.alter_column("quiz_sessions", "user_id", nullable=True, schema="spanglish")
    op.drop_index(
        "ix_refresh_sessions_user_id",
        table_name="refresh_sessions",
        schema="public",
    )
    op.drop_table("refresh_sessions", schema="public")
