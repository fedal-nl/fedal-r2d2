"""split application schemas and add Resend fields

Revision ID: b51d8c9a4f20
Revises: 2797ca993b35
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b51d8c9a4f20"
down_revision: str | Sequence[str] | None = "2797ca993b35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SPANGGLISH_TABLES = (
    "ai_agents",
    "ai_usage",
    "categories",
    "chapters",
    "languages",
    "quiz_attempts",
    "quiz_sessions",
    "translations",
    "verb_conjugations",
    "vocabulary",
    "vocabulary_categories",
    "vocabulary_examples",
    "vocabulary_types",
)


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS spanglish"))
    for table_name in SPANGGLISH_TABLES:
        op.execute(sa.text(f'ALTER TABLE public."{table_name}" SET SCHEMA spanglish'))

    op.add_column(
        "email_logs",
        sa.Column("application", sa.String(), server_default="general", nullable=False),
        schema="public",
    )
    op.add_column(
        "email_logs",
        sa.Column("provider_message_id", sa.String(), nullable=True),
        schema="public",
    )
    op.alter_column("email_logs", "application", server_default=None, schema="public")


def downgrade() -> None:
    op.drop_column("email_logs", "provider_message_id", schema="public")
    op.drop_column("email_logs", "application", schema="public")

    for table_name in reversed(SPANGGLISH_TABLES):
        op.execute(sa.text(f'ALTER TABLE spanglish."{table_name}" SET SCHEMA public'))
    op.execute(sa.text("DROP SCHEMA spanglish"))
