"""Remove redundant vocabulary types.

Revision ID: b72e4a9c1d30
Revises: a41f8c7d2e90
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b72e4a9c1d30"
down_revision: str | Sequence[str] | None = "a41f8c7d2e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the vocabulary type association and lookup table."""
    op.drop_constraint(
        "vocabulary_vocabulary_type_id_fkey",
        "vocabulary",
        schema="spanglish",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_vocabulary_vocabulary_type_id",
        table_name="vocabulary",
        schema="spanglish",
    )
    op.drop_column("vocabulary", "vocabulary_type_id", schema="spanglish")
    op.drop_table("vocabulary_types", schema="spanglish")


def downgrade() -> None:
    """Restore vocabulary types and assign existing rows to the Word type."""
    op.create_table(
        "vocabulary_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("name", name="uq_vocabularytype_name"),
        schema="spanglish",
    )
    op.create_index(
        "ix_vocabulary_types_name", "vocabulary_types", ["name"], schema="spanglish"
    )
    op.execute(sa.text("INSERT INTO spanglish.vocabulary_types (name) VALUES ('Word')"))
    op.add_column(
        "vocabulary",
        sa.Column("vocabulary_type_id", sa.Integer(), nullable=True),
        schema="spanglish",
    )
    op.execute(
        sa.text(
            "UPDATE spanglish.vocabulary SET vocabulary_type_id = "
            "(SELECT id FROM spanglish.vocabulary_types WHERE name = 'Word')"
        )
    )
    op.alter_column(
        "vocabulary", "vocabulary_type_id", nullable=False, schema="spanglish"
    )
    op.create_foreign_key(
        "vocabulary_vocabulary_type_id_fkey",
        "vocabulary",
        "vocabulary_types",
        ["vocabulary_type_id"],
        ["id"],
        source_schema="spanglish",
        referent_schema="spanglish",
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_vocabulary_vocabulary_type_id",
        "vocabulary",
        ["vocabulary_type_id"],
        schema="spanglish",
    )
