"""Normalize vocabulary text to sentence-style capitalization.

Revision ID: f19c7a4d8e32
Revises: e84f6a1c2b90
"""

from alembic import op
import sqlalchemy as sa

revision = "f19c7a4d8e32"
down_revision = "e84f6a1c2b90"
branch_labels = None
depends_on = None


NORMALIZED_TEXT = "upper(left(btrim(text), 1)) || lower(substring(btrim(text) from 2))"


def upgrade() -> None:
    """Capitalize only the first character of every vocabulary text."""
    # Normalization can make differently-cased rows identical. Abort with a
    # useful error instead of silently merging learner data or failing midway.
    op.execute(sa.text(f"""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM spanglish.vocabulary
                GROUP BY user_id, language_id, {NORMALIZED_TEXT}
                HAVING count(*) > 1
              ) THEN
                RAISE EXCEPTION
                  'Vocabulary capitalization would create duplicate rows';
              END IF;
            END $$;
            """))
    op.execute(sa.text(f"""
            UPDATE spanglish.vocabulary
            SET text = {NORMALIZED_TEXT}
            WHERE text IS DISTINCT FROM {NORMALIZED_TEXT}
            """))


def downgrade() -> None:
    """Leave normalized casing unchanged because the original case is unknown."""
    pass
