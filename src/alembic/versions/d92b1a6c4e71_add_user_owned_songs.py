"""Add user-owned artists and songs and link vocabulary to songs.

Revision ID: d92b1a6c4e71
Revises: b72e4a9c1d30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d92b1a6c4e71"
down_revision: str | Sequence[str] | None = "b72e4a9c1d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist songs and allow each learner to own named references."""
    legacy_user_id = "00000000-0000-0000-0000-000000000001"
    op.execute(
        sa.text(
            "INSERT INTO public.users (id, username, is_active) "
            "VALUES (:user_id, 'legacy_anonymous', false) ON CONFLICT DO NOTHING"
        ).bindparams(user_id=legacy_user_id)
    )
    op.execute(
        sa.text(
            "UPDATE spanglish.vocabulary SET user_id = :user_id WHERE user_id IS NULL"
        ).bindparams(user_id=legacy_user_id)
    )
    op.alter_column("vocabulary", "user_id", nullable=False, schema="spanglish")
    for field in ("name", "code"):
        op.drop_constraint(
            f"uq_language_{field}", "languages", schema="spanglish", type_="unique"
        )
        op.create_unique_constraint(
            f"uq_languages_user_{field}",
            "languages",
            ["user_id", field],
            schema="spanglish",
        )
    for table, parent, parent_id in (
        ("vocabulary_categories", "vocabulary", "vocabulary_id"),
        ("verb_conjugations", "vocabulary", "vocabulary_id"),
        ("vocabulary_examples", "vocabulary", "vocabulary_id"),
        ("translations", "vocabulary", "vocabulary_id"),
        ("quiz_attempts", "quiz_sessions", "session_id"),
    ):
        op.add_column(
            table,
            sa.Column("user_id", postgresql.UUID(as_uuid=True)),
            schema="spanglish",
        )
        op.execute(
            sa.text(
                f"UPDATE spanglish.{table} AS child SET user_id = parent.user_id "
                f"FROM spanglish.{parent} AS parent WHERE child.{parent_id} = parent.id"
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
    op.execute(
        sa.text("""
        CREATE FUNCTION spanglish.set_child_user_id() RETURNS trigger AS $$
        BEGIN
            IF TG_TABLE_NAME = 'quiz_attempts' THEN
                SELECT user_id INTO NEW.user_id FROM spanglish.quiz_sessions WHERE id = NEW.session_id;
            ELSE
                SELECT user_id INTO NEW.user_id FROM spanglish.vocabulary WHERE id = NEW.vocabulary_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    )
    for table in (
        "vocabulary_categories",
        "verb_conjugations",
        "vocabulary_examples",
        "translations",
        "quiz_attempts",
    ):
        op.execute(
            sa.text(
                f"CREATE TRIGGER trg_{table}_user_id BEFORE INSERT OR UPDATE ON spanglish.{table} FOR EACH ROW EXECUTE FUNCTION spanglish.set_child_user_id()"
            )
        )
    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_artist_user_name"),
        schema="spanglish",
    )
    op.create_index("ix_artists_user_id", "artists", ["user_id"], schema="spanglish")
    op.create_table(
        "songs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artist_id",
            sa.Integer(),
            sa.ForeignKey("spanglish.artists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "artist_id", "title", name="uq_song_user_artist_title"
        ),
        schema="spanglish",
    )
    op.create_index("ix_songs_user_id", "songs", ["user_id"], schema="spanglish")
    op.create_index("ix_songs_artist_id", "songs", ["artist_id"], schema="spanglish")
    op.add_column(
        "vocabulary",
        sa.Column("song_id", sa.Integer(), nullable=True),
        schema="spanglish",
    )
    op.create_foreign_key(
        "fk_vocabulary_song_id",
        "vocabulary",
        "songs",
        ["song_id"],
        ["id"],
        source_schema="spanglish",
        referent_schema="spanglish",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_vocabulary_song_id", "vocabulary", ["song_id"], schema="spanglish"
    )
    for table in ("categories", "chapters"):
        old_name = "uq_category_name" if table == "categories" else "uq_chapter_name"
        op.drop_constraint(old_name, table, schema="spanglish", type_="unique")
        op.create_unique_constraint(
            f"uq_{table}_user_name", table, ["user_id", "name"], schema="spanglish"
        )
    # Keep the ownerless seed rows as templates, but give every existing account
    # private copies and move its existing vocabulary/quiz references to them.
    for table, fields in (
        ("languages", "name, code"),
        ("categories", "name"),
        ("chapters", "name"),
    ):
        source_fields = ", ".join(
            f"templates.{column.strip()}" for column in fields.split(",")
        )
        op.execute(
            sa.text(
                f"INSERT INTO spanglish.{table} ({fields}, user_id) "
                f"SELECT {source_fields}, users.id FROM spanglish.{table} AS templates "
                "CROSS JOIN public.users AS users WHERE templates.user_id IS NULL "
                "ON CONFLICT DO NOTHING"
            )
        )
    for table, foreign_key, reference, match in (
        ("vocabulary", "language_id", "languages", "code"),
        ("translations", "language_id", "languages", "code"),
        ("quiz_sessions", "source_language_id", "languages", "code"),
        ("quiz_sessions", "target_language_id", "languages", "code"),
        ("vocabulary", "chapter_id", "chapters", "name"),
        ("vocabulary_categories", "category_id", "categories", "name"),
    ):
        op.execute(
            sa.text(
                f"UPDATE spanglish.{table} AS owned SET {foreign_key} = personal.id "
                f"FROM spanglish.{reference} AS template, spanglish.{reference} AS personal "
                f"WHERE owned.{foreign_key} = template.id AND template.user_id IS NULL "
                f"AND personal.user_id = owned.user_id AND personal.{match} = template.{match}"
            )
        )


def downgrade() -> None:
    """Remove songs and restore globally unique reference names."""
    for field in ("name", "code"):
        op.drop_constraint(
            f"uq_languages_user_{field}",
            "languages",
            schema="spanglish",
            type_="unique",
        )
        op.create_unique_constraint(
            f"uq_language_{field}", "languages", [field], schema="spanglish"
        )
    for table in (
        "vocabulary_categories",
        "verb_conjugations",
        "vocabulary_examples",
        "translations",
        "quiz_attempts",
    ):
        op.execute(sa.text(f"DROP TRIGGER trg_{table}_user_id ON spanglish.{table}"))
    op.execute(sa.text("DROP FUNCTION spanglish.set_child_user_id()"))
    for table in (
        "vocabulary_categories",
        "verb_conjugations",
        "vocabulary_examples",
        "translations",
        "quiz_attempts",
    ):
        op.drop_index(f"ix_{table}_user_id", table_name=table, schema="spanglish")
        op.drop_constraint(
            f"fk_{table}_user_id", table, schema="spanglish", type_="foreignkey"
        )
        op.drop_column(table, "user_id", schema="spanglish")
    op.alter_column("vocabulary", "user_id", nullable=True, schema="spanglish")
    for table in ("categories", "chapters"):
        op.drop_constraint(
            f"uq_{table}_user_name", table, schema="spanglish", type_="unique"
        )
        old_name = "uq_category_name" if table == "categories" else "uq_chapter_name"
        op.create_unique_constraint(old_name, table, ["name"], schema="spanglish")
    op.drop_index("ix_vocabulary_song_id", table_name="vocabulary", schema="spanglish")
    op.drop_constraint(
        "fk_vocabulary_song_id", "vocabulary", schema="spanglish", type_="foreignkey"
    )
    op.drop_column("vocabulary", "song_id", schema="spanglish")
    op.drop_table("songs", schema="spanglish")
    op.drop_table("artists", schema="spanglish")
