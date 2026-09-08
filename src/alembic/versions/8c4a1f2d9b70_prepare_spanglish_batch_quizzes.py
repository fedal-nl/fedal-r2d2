"""Prepare Spanglish reference data and batch quiz snapshots.

Revision ID: 8c4a1f2d9b70
Revises: e065eb46edec
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c4a1f2d9b70"
down_revision: str | Sequence[str] | None = "e065eb46edec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Evolve existing Spanglish tables without modifying shared services."""
    for table_name in ("languages", "vocabulary_types", "categories", "chapters", "vocabulary", "quiz_sessions"):
        op.alter_column(table_name, "user_id", existing_type=postgresql.UUID(), nullable=True, schema="spanglish")

    op.drop_constraint("uq_language_name_user", "languages", schema="spanglish", type_="unique")
    op.drop_constraint("uq_language_code_user", "languages", schema="spanglish", type_="unique")
    op.create_unique_constraint("uq_language_name", "languages", ["name"], schema="spanglish")
    op.create_unique_constraint("uq_language_code", "languages", ["code"], schema="spanglish")
    op.drop_constraint("uq_vocabularytype_name_user", "vocabulary_types", schema="spanglish", type_="unique")
    op.create_unique_constraint("uq_vocabularytype_name", "vocabulary_types", ["name"], schema="spanglish")
    op.drop_constraint("uq_category_name_user", "categories", schema="spanglish", type_="unique")
    op.create_unique_constraint("uq_category_name", "categories", ["name"], schema="spanglish")
    op.drop_constraint("uq_chapter_name_user", "chapters", schema="spanglish", type_="unique")
    op.create_unique_constraint("uq_chapter_name", "chapters", ["name"], schema="spanglish")
    op.drop_constraint("uq_vocabulary_text_language_user", "vocabulary", schema="spanglish", type_="unique")
    op.create_unique_constraint("uq_vocabulary_text_language", "vocabulary", ["text", "language_id"], schema="spanglish")

    op.add_column("verb_conjugations", sa.Column("tense", sa.String(), server_default="present", nullable=False), schema="spanglish")
    op.add_column("verb_conjugations", sa.Column("mood", sa.String(), server_default="indicative", nullable=False), schema="spanglish")
    op.add_column("verb_conjugations", sa.Column("pronoun", sa.String(), server_default="legacy", nullable=False), schema="spanglish")
    op.add_column("verb_conjugations", sa.Column("form", sa.String(), nullable=True), schema="spanglish")
    op.execute(sa.text("UPDATE spanglish.verb_conjugations SET form = conjugation"))
    op.alter_column("verb_conjugations", "form", nullable=False, schema="spanglish")
    op.drop_column("verb_conjugations", "conjugation", schema="spanglish")
    op.create_unique_constraint("uq_verb_form", "verb_conjugations", ["vocabulary_id", "tense", "mood", "pronoun"], schema="spanglish")

    op.drop_constraint("translations_vocabulary_id_translation_key", "translations", schema="spanglish", type_="unique")
    op.create_unique_constraint("uq_translation", "translations", ["vocabulary_id", "language_id", "translation"], schema="spanglish")

    quiz_columns = (
        sa.Column("source_language_id", sa.Integer(), nullable=True),
        sa.Column("target_language_id", sa.Integer(), nullable=True),
        sa.Column("selection_mode", sa.String(), nullable=True),
        sa.Column("requested_question_count", sa.Integer(), nullable=True),
        sa.Column("actual_question_count", sa.Integer(), nullable=True),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("client_type", sa.String(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correct_count", sa.Integer(), nullable=True),
        sa.Column("score_percentage", sa.Float(), nullable=True),
        sa.Column("advice", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    for column in quiz_columns:
        op.add_column("quiz_sessions", column, schema="spanglish")
    op.create_foreign_key("fk_quiz_source_language", "quiz_sessions", "languages", ["source_language_id"], ["id"], source_schema="spanglish", referent_schema="spanglish")
    op.create_foreign_key("fk_quiz_target_language", "quiz_sessions", "languages", ["target_language_id"], ["id"], source_schema="spanglish", referent_schema="spanglish")
    op.create_index("ix_quiz_sessions_source_language_id", "quiz_sessions", ["source_language_id"], schema="spanglish")
    op.create_index("ix_quiz_sessions_target_language_id", "quiz_sessions", ["target_language_id"], schema="spanglish")

    op.add_column("quiz_attempts", sa.Column("question_id", sa.String(), nullable=True), schema="spanglish")
    op.add_column("quiz_attempts", sa.Column("expected_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema="spanglish")
    op.add_column("quiz_attempts", sa.Column("score", sa.Float(), nullable=True), schema="spanglish")
    op.add_column("quiz_attempts", sa.Column("response_time_ms", sa.Integer(), nullable=True), schema="spanglish")
    op.add_column("quiz_attempts", sa.Column("feedback", sa.String(), nullable=True), schema="spanglish")
    op.execute(sa.text("UPDATE spanglish.quiz_attempts SET question_id = 'legacy-' || id, expected_answers = '[]'::jsonb, score = CASE WHEN answered_correctly THEN 1.0 ELSE 0.0 END"))
    op.alter_column("quiz_attempts", "answer", type_=postgresql.JSONB(astext_type=sa.Text()), postgresql_using="jsonb_build_object('value', answer)", schema="spanglish")
    op.alter_column("quiz_attempts", "question_id", nullable=False, schema="spanglish")
    op.alter_column("quiz_attempts", "expected_answers", nullable=False, schema="spanglish")
    op.alter_column("quiz_attempts", "score", nullable=False, schema="spanglish")
    op.create_unique_constraint("uq_quiz_question_attempt", "quiz_attempts", ["session_id", "question_id"], schema="spanglish")

    op.execute(sa.text("INSERT INTO spanglish.languages (name, code) VALUES ('Spanish', 'es'), ('English', 'en') ON CONFLICT DO NOTHING"))
    op.execute(sa.text("INSERT INTO spanglish.vocabulary_types (name) VALUES ('Word'), ('Phrase'), ('Sentence'), ('Lyric') ON CONFLICT DO NOTHING"))
    category_values = ("Noun", "Verb", "Adjective", "Days", "Months", "Colors", "Body Parts", "Animals", "Family", "Numbers", "Time", "Directions", "Greetings", "Weather", "Songs", "Food", "Professions", "Phrases")
    values = ", ".join("('" + value.replace("'", "''") + "')" for value in category_values)
    op.execute(sa.text(f"INSERT INTO spanglish.categories (name) VALUES {values} ON CONFLICT DO NOTHING"))


def downgrade() -> None:
    """Restore the former CLI-inspired storage shape while preserving shared tables."""
    op.drop_constraint("uq_quiz_question_attempt", "quiz_attempts", schema="spanglish", type_="unique")
    op.alter_column("quiz_attempts", "answer", type_=sa.String(), postgresql_using="answer->>'value'", schema="spanglish")
    for column in ("feedback", "response_time_ms", "score", "expected_answers", "question_id"):
        op.drop_column("quiz_attempts", column, schema="spanglish")
    op.drop_index("ix_quiz_sessions_target_language_id", table_name="quiz_sessions", schema="spanglish")
    op.drop_index("ix_quiz_sessions_source_language_id", table_name="quiz_sessions", schema="spanglish")
    op.drop_constraint("fk_quiz_target_language", "quiz_sessions", schema="spanglish", type_="foreignkey")
    op.drop_constraint("fk_quiz_source_language", "quiz_sessions", schema="spanglish", type_="foreignkey")
    for column in ("advice", "score_percentage", "correct_count", "completed_at", "client_type", "questions", "configuration", "actual_question_count", "requested_question_count", "selection_mode", "target_language_id", "source_language_id"):
        op.drop_column("quiz_sessions", column, schema="spanglish")
    op.drop_constraint("uq_translation", "translations", schema="spanglish", type_="unique")
    op.create_unique_constraint(None, "translations", ["vocabulary_id", "translation"], schema="spanglish")
    op.drop_constraint("uq_verb_form", "verb_conjugations", schema="spanglish", type_="unique")
    op.add_column("verb_conjugations", sa.Column("conjugation", sa.String(), nullable=True), schema="spanglish")
    op.execute(sa.text("UPDATE spanglish.verb_conjugations SET conjugation = form"))
    op.alter_column("verb_conjugations", "conjugation", nullable=False, schema="spanglish")
    for column in ("form", "pronoun", "mood", "tense"):
        op.drop_column("verb_conjugations", column, schema="spanglish")
