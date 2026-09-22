"""Refactor Spanglish ownership and backfill root records.

Revision ID: e84f6a1c2b90
Revises: d92b1a6c4e71
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e84f6a1c2b90"
down_revision = "d92b1a6c4e71"
branch_labels = None
depends_on = None

CHILD_TABLES = (
    "vocabulary_categories",
    "verb_conjugations",
    "vocabulary_examples",
    "translations",
    "quiz_attempts",
)


def upgrade() -> None:
    """Backfill roots, then remove ownership duplicated by parent relations."""
    # d92 created per-user copies of nullable seed templates. Consolidate the
    # first user's copy back into each template before assigning its owner.
    op.execute(sa.text("""
            DO $$
            DECLARE first_user uuid;
            BEGIN
              SELECT id INTO first_user FROM public.users
              WHERE id <> '00000000-0000-0000-0000-000000000001'::uuid
              ORDER BY created_at, id LIMIT 1;
              IF first_user IS NULL THEN
                SELECT id INTO first_user FROM public.users ORDER BY created_at, id LIMIT 1;
              END IF;
              IF first_user IS NULL THEN
                RAISE EXCEPTION 'Cannot backfill Spanglish ownership without a user';
              END IF;

              UPDATE spanglish.vocabulary v SET language_id = t.id
              FROM spanglish.languages p, spanglish.languages t
              WHERE p.user_id = first_user AND t.user_id IS NULL
                AND p.code = t.code AND v.language_id = p.id;
              UPDATE spanglish.translations x SET language_id = t.id
              FROM spanglish.languages p, spanglish.languages t
              WHERE p.user_id = first_user AND t.user_id IS NULL
                AND p.code = t.code AND x.language_id = p.id;
              UPDATE spanglish.quiz_sessions q SET source_language_id = t.id
              FROM spanglish.languages p, spanglish.languages t
              WHERE p.user_id = first_user AND t.user_id IS NULL
                AND p.code = t.code AND q.source_language_id = p.id;
              UPDATE spanglish.quiz_sessions q SET target_language_id = t.id
              FROM spanglish.languages p, spanglish.languages t
              WHERE p.user_id = first_user AND t.user_id IS NULL
                AND p.code = t.code AND q.target_language_id = p.id;
              DELETE FROM spanglish.languages p USING spanglish.languages t
              WHERE p.user_id = first_user AND t.user_id IS NULL AND p.code = t.code;

              UPDATE spanglish.vocabulary_categories vc SET category_id = t.id
              FROM spanglish.categories p, spanglish.categories t
              WHERE p.user_id = first_user AND t.user_id IS NULL
                AND p.name = t.name AND vc.category_id = p.id;
              DELETE FROM spanglish.categories p USING spanglish.categories t
              WHERE p.user_id = first_user AND t.user_id IS NULL AND p.name = t.name;

              UPDATE spanglish.vocabulary v SET chapter_id = t.id
              FROM spanglish.chapters p, spanglish.chapters t
              WHERE p.user_id = first_user AND t.user_id IS NULL
                AND p.name = t.name AND v.chapter_id = p.id;
              DELETE FROM spanglish.chapters p USING spanglish.chapters t
              WHERE p.user_id = first_user AND t.user_id IS NULL AND p.name = t.name;

              UPDATE spanglish.languages SET user_id = first_user WHERE user_id IS NULL;
              UPDATE spanglish.categories SET user_id = first_user WHERE user_id IS NULL;
              UPDATE spanglish.chapters SET user_id = first_user WHERE user_id IS NULL;
              UPDATE spanglish.vocabulary SET user_id = first_user
              WHERE user_id IS NULL OR user_id = '00000000-0000-0000-0000-000000000001'::uuid;
              UPDATE spanglish.quiz_sessions SET user_id = first_user WHERE user_id IS NULL;
            END $$;
            """))
    for table in ("languages", "categories", "chapters", "vocabulary"):
        op.alter_column(table, "user_id", nullable=False, schema="spanglish")

    for table in CHILD_TABLES:
        op.execute(
            sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_user_id ON spanglish.{table}")
        )
    op.execute(sa.text("DROP FUNCTION IF EXISTS spanglish.set_child_user_id()"))

    for table in CHILD_TABLES:
        op.drop_index(f"ix_{table}_user_id", table_name=table, schema="spanglish")
        op.drop_constraint(
            f"fk_{table}_user_id", table, schema="spanglish", type_="foreignkey"
        )
        op.drop_column(table, "user_id", schema="spanglish")

    op.drop_constraint(
        "uq_song_user_artist_title", "songs", schema="spanglish", type_="unique"
    )
    op.drop_index("ix_songs_user_id", table_name="songs", schema="spanglish")
    op.drop_column("songs", "user_id", schema="spanglish")
    op.create_unique_constraint(
        "uq_song_artist_title", "songs", ["artist_id", "title"], schema="spanglish"
    )


def downgrade() -> None:
    """Restore denormalized ownership columns from their owning parents."""
    op.drop_constraint(
        "uq_song_artist_title", "songs", schema="spanglish", type_="unique"
    )
    op.add_column(
        "songs", sa.Column("user_id", postgresql.UUID(as_uuid=True)), schema="spanglish"
    )
    op.execute(
        sa.text(
            "UPDATE spanglish.songs s SET user_id = a.user_id FROM spanglish.artists a WHERE a.id = s.artist_id"
        )
    )
    op.alter_column("songs", "user_id", nullable=False, schema="spanglish")
    op.create_foreign_key(
        "fk_songs_user_id",
        "songs",
        "users",
        ["user_id"],
        ["id"],
        source_schema="spanglish",
        referent_schema="public",
        ondelete="CASCADE",
    )
    op.create_index("ix_songs_user_id", "songs", ["user_id"], schema="spanglish")
    op.create_unique_constraint(
        "uq_song_user_artist_title",
        "songs",
        ["user_id", "artist_id", "title"],
        schema="spanglish",
    )

    parents = {
        "quiz_attempts": ("quiz_sessions", "session_id"),
        **{
            table: ("vocabulary", "vocabulary_id")
            for table in CHILD_TABLES
            if table != "quiz_attempts"
        },
    }
    for table, (parent, key) in parents.items():
        op.add_column(
            table,
            sa.Column("user_id", postgresql.UUID(as_uuid=True)),
            schema="spanglish",
        )
        op.execute(
            sa.text(
                f"UPDATE spanglish.{table} c SET user_id = p.user_id FROM spanglish.{parent} p WHERE p.id = c.{key}"
            )
        )
        op.alter_column(table, "user_id", nullable=False, schema="spanglish")
        op.create_foreign_key(
            f"fk_{table}_user_id",
            table,
            "users",
            ["user_id"],
            ["id"],
            source_schema="spanglish",
            referent_schema="public",
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"], schema="spanglish")

    for table in ("languages", "categories", "chapters"):
        op.alter_column(table, "user_id", nullable=True, schema="spanglish")
