"""Normalize translations to sentence-style capitalization.

Revision ID: a27d5e9f3c41
Revises: f19c7a4d8e32
"""

from alembic import op
import sqlalchemy as sa

revision = "a27d5e9f3c41"
down_revision = "f19c7a4d8e32"
branch_labels = None
depends_on = None


NORMALIZED_TRANSLATION = (
    "upper(left(btrim(translation), 1)) "
    "|| lower(substring(btrim(translation) from 2))"
)


def upgrade() -> None:
    """Capitalize only the first character of every translation."""
    # The unique constraint includes vocabulary and language. Detect casing
    # collisions before changing any learner data.
    op.execute(sa.text(f"""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM spanglish.translations
                GROUP BY vocabulary_id, language_id, {NORMALIZED_TRANSLATION}
                HAVING count(*) > 1
              ) THEN
                RAISE EXCEPTION
                  'Translation capitalization would create duplicate rows';
              END IF;
            END $$;
            """))
    op.execute(sa.text(f"""
            UPDATE spanglish.translations
            SET translation = {NORMALIZED_TRANSLATION}
            WHERE translation IS DISTINCT FROM {NORMALIZED_TRANSLATION}
            """))


def downgrade() -> None:
    """Leave normalized casing unchanged because the original case is unknown."""
    pass
