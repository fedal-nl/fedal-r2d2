"""Move AI persistence into a shared schema and generalize usage tracking.

Revision ID: c7d2e4f8a901
Revises: 8c4a1f2d9b70
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7d2e4f8a901"
down_revision: str | Sequence[str] | None = "8c4a1f2d9b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move existing AI data and add application-neutral configuration fields."""
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS ai"))
    op.execute(sa.text("ALTER TABLE spanglish.ai_agents SET SCHEMA ai"))
    op.execute(sa.text("ALTER TABLE spanglish.ai_usage SET SCHEMA ai"))

    op.drop_constraint("ai_agents_name_key", "ai_agents", schema="ai", type_="unique")
    op.add_column(
        "ai_agents",
        sa.Column("application", sa.String(), server_default="general", nullable=False),
        schema="ai",
    )
    op.add_column(
        "ai_agents",
        sa.Column("feature", sa.String(), server_default="generation", nullable=False),
        schema="ai",
    )
    op.add_column(
        "ai_agents",
        sa.Column("model_name", sa.String(), server_default="unspecified", nullable=False),
        schema="ai",
    )
    op.add_column(
        "ai_agents",
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        schema="ai",
    )
    op.create_unique_constraint(
        "uq_ai_prompt_version",
        "ai_agents",
        ["application", "feature", "prompt_version"],
        schema="ai",
    )
    op.create_index("ix_ai_agents_name", "ai_agents", ["name"], schema="ai")
    op.create_index(
        "ix_ai_agents_application", "ai_agents", ["application"], schema="ai"
    )
    op.create_index("ix_ai_agents_feature", "ai_agents", ["feature"], schema="ai")

    op.alter_column(
        "ai_usage",
        "user_id",
        existing_type=postgresql.UUID(),
        nullable=True,
        schema="ai",
    )
    op.drop_constraint(
        "ai_usage_user_id_fkey", "ai_usage", schema="ai", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_ai_usage_user",
        "ai_usage",
        "users",
        ["user_id"],
        ["id"],
        source_schema="ai",
        referent_schema="public",
        ondelete="SET NULL",
    )
    usage_columns = (
        sa.Column("application", sa.String(), nullable=True),
        sa.Column("feature", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("error_code", sa.String(), nullable=True),
    )
    for column in usage_columns:
        op.add_column("ai_usage", column, schema="ai")
    op.execute(
        sa.text(
            "UPDATE ai.ai_usage AS usage "
            "SET application = agent.application, feature = agent.feature, "
            "input_tokens = usage.tokens_used "
            "FROM ai.ai_agents AS agent WHERE usage.ai_agent_id = agent.id"
        )
    )
    op.alter_column("ai_usage", "application", nullable=False, schema="ai")
    op.alter_column("ai_usage", "feature", nullable=False, schema="ai")
    op.create_index(
        "ix_ai_usage_ai_agent_id", "ai_usage", ["ai_agent_id"], schema="ai"
    )
    op.create_index(
        "ix_ai_usage_application", "ai_usage", ["application"], schema="ai"
    )
    op.create_index("ix_ai_usage_feature", "ai_usage", ["feature"], schema="ai")
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"], schema="ai")


def downgrade() -> None:
    """Restore the former Spanglish-owned AI tables and their original columns."""
    for index_name in (
        "ix_ai_usage_created_at",
        "ix_ai_usage_feature",
        "ix_ai_usage_application",
        "ix_ai_usage_ai_agent_id",
    ):
        op.drop_index(index_name, table_name="ai_usage", schema="ai")
    for column in (
        "error_code",
        "success",
        "latency_ms",
        "output_tokens",
        "input_tokens",
        "feature",
        "application",
    ):
        op.drop_column("ai_usage", column, schema="ai")
    op.drop_constraint("fk_ai_usage_user", "ai_usage", schema="ai", type_="foreignkey")
    op.create_foreign_key(
        "ai_usage_user_id_fkey",
        "ai_usage",
        "users",
        ["user_id"],
        ["id"],
        source_schema="ai",
        referent_schema="public",
    )
    op.alter_column(
        "ai_usage",
        "user_id",
        existing_type=postgresql.UUID(),
        nullable=False,
        schema="ai",
    )

    op.drop_index("ix_ai_agents_feature", table_name="ai_agents", schema="ai")
    op.drop_index("ix_ai_agents_application", table_name="ai_agents", schema="ai")
    op.drop_index("ix_ai_agents_name", table_name="ai_agents", schema="ai")
    op.drop_constraint("uq_ai_prompt_version", "ai_agents", schema="ai", type_="unique")
    for column in ("enabled", "model_name", "feature", "application"):
        op.drop_column("ai_agents", column, schema="ai")
    op.create_unique_constraint(None, "ai_agents", ["name"], schema="ai")

    op.execute(sa.text("ALTER TABLE ai.ai_usage SET SCHEMA spanglish"))
    op.execute(sa.text("ALTER TABLE ai.ai_agents SET SCHEMA spanglish"))
    op.execute(sa.text("DROP SCHEMA ai"))
