"""Database models for the isolated Spanglish application."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.core.database import Base

SPANGGLISH_SCHEMA = "spanglish"


class Language(Base):
    """A language available as a quiz source or target."""

    __tablename__ = "languages"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Language identifier")
    name: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Human-readable language name"
    )
    code: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Short language code"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the language was created",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        index=True,
        comment="Time the language was last updated",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns the language",
    )
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_languages_user_name"),
        UniqueConstraint("user_id", "code", name="uq_languages_user_code"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Category(Base):
    """A topic used to browse vocabulary and configure quizzes."""

    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Category identifier")
    name: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Category display name"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the category was created",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        index=True,
        comment="Time the category was last updated",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns the category",
    )
    vocabularies: Mapped[list["Vocabulary"]] = relationship(
        secondary="spanglish.vocabulary_categories", back_populates="categories"
    )
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Chapter(Base):
    """An optional collection that groups vocabulary into a lesson."""

    __tablename__ = "chapters"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Chapter identifier")
    name: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Chapter display name"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the chapter was created",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        index=True,
        comment="Time the chapter was last updated",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns the chapter",
    )
    vocabulary: Mapped[list["Vocabulary"]] = relationship(back_populates="chapter")
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_chapters_user_name"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Artist(Base):
    """A user-owned performer with independently selectable songs."""

    __tablename__ = "artists"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Artist identifier")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns the artist",
    )
    name: Mapped[str] = mapped_column(
        String, nullable=False, comment="Artist or performer name"
    )
    songs: Mapped[list["Song"]] = relationship(back_populates="artist")
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_artist_user_name"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Song(Base):
    """A title whose owner is derived from its performer."""

    __tablename__ = "songs"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Song identifier")
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Artist who performs the song",
    )
    title: Mapped[str] = mapped_column(String, nullable=False, comment="Song title")
    artist: Mapped[Artist] = relationship(back_populates="songs")
    vocabularies: Mapped[list["Vocabulary"]] = relationship(back_populates="song")
    __table_args__ = (
        UniqueConstraint("artist_id", "title", name="uq_song_artist_title"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Vocabulary(Base):
    """A source-language term with translations and learning metadata."""

    __tablename__ = "vocabulary"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Vocabulary identifier")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns the vocabulary",
    )
    text: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Source vocabulary text"
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.languages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Language of the source text",
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.chapters.id", ondelete="SET NULL"),
        index=True,
        comment="Optional chapter containing the vocabulary",
    )
    song_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.songs.id", ondelete="SET NULL"),
        index=True,
        comment="Optional song containing this lyric",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the vocabulary was created",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        index=True,
        comment="Time the vocabulary was last updated",
    )
    language: Mapped[Language] = relationship()
    chapter: Mapped[Chapter | None] = relationship(back_populates="vocabulary")
    song: Mapped[Song | None] = relationship(back_populates="vocabularies")
    translations: Mapped[list["Translation"]] = relationship(
        back_populates="vocabulary", cascade="all, delete-orphan"
    )
    verb_conjugations: Mapped[list["VerbConjugation"]] = relationship(
        back_populates="vocabulary", cascade="all, delete-orphan"
    )
    examples: Mapped[list["VocabularyExample"]] = relationship(
        back_populates="vocabulary", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="vocabulary")
    categories: Mapped[list[Category]] = relationship(
        secondary="spanglish.vocabulary_categories", back_populates="vocabularies"
    )
    __table_args__ = (
        UniqueConstraint(
            "text",
            "language_id",
            "user_id",
            name="uq_vocabulary_text_language_user",
        ),
        {"schema": SPANGGLISH_SCHEMA},
    )


class VocabularyCategory(Base):
    """Association between vocabulary and one or more topics."""

    __tablename__ = "vocabulary_categories"
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Associated vocabulary identifier",
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.categories.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Associated category identifier",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the category was assigned",
    )
    __table_args__ = {"schema": SPANGGLISH_SCHEMA}


class VerbConjugation(Base):
    """A structured verb form that can become a quiz item."""

    __tablename__ = "verb_conjugations"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Conjugation identifier")
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Vocabulary verb being conjugated",
    )
    tense: Mapped[str] = mapped_column(
        String, nullable=False, default="present", comment="Grammatical tense"
    )
    mood: Mapped[str] = mapped_column(
        String, nullable=False, default="indicative", comment="Grammatical mood"
    )
    pronoun: Mapped[str] = mapped_column(
        String, nullable=False, comment="Pronoun associated with the form"
    )
    form: Mapped[str] = mapped_column(
        String, nullable=False, comment="Conjugated verb form"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the conjugation was created",
    )
    vocabulary: Mapped[Vocabulary] = relationship(back_populates="verb_conjugations")
    __table_args__ = (
        UniqueConstraint(
            "vocabulary_id", "tense", "mood", "pronoun", name="uq_verb_form"
        ),
        {"schema": SPANGGLISH_SCHEMA},
    )


class VocabularyExample(Base):
    """A translated usage example, optionally created by an AI agent."""

    __tablename__ = "vocabulary_examples"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Example identifier")
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Vocabulary illustrated by the example",
    )
    ai_agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai.ai_agents.id", ondelete="SET NULL"),
        index=True,
        comment="Optional AI agent that generated the example",
    )
    example: Mapped[str] = mapped_column(
        String, nullable=False, comment="Usage example in the source language"
    )
    translation: Mapped[str] = mapped_column(
        String, nullable=False, comment="Translation of the usage example"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the example was created",
    )
    vocabulary: Mapped[Vocabulary] = relationship(back_populates="examples")
    __table_args__ = {"schema": SPANGGLISH_SCHEMA}


VocabularyExamples = VocabularyExample


class Translation(Base):
    """One accepted translation for a vocabulary item."""

    __tablename__ = "translations"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Translation identifier")
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Vocabulary being translated",
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.languages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Language of the translated text",
    )
    translation: Mapped[str] = mapped_column(
        String, nullable=False, comment="Accepted translated text"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the translation was created",
    )
    vocabulary: Mapped[Vocabulary] = relationship(back_populates="translations")
    language: Mapped[Language] = relationship()
    __table_args__ = (
        UniqueConstraint(
            "vocabulary_id", "language_id", "translation", name="uq_translation"
        ),
        {"schema": SPANGGLISH_SCHEMA},
    )


class QuizSession(Base):
    """An immutable generated quiz snapshot plus its optional final result."""

    __tablename__ = "quiz_sessions"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Quiz session identifier")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns the quiz session",
    )
    source_language_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.languages.id"),
        index=True,
        comment="Language shown in quiz prompts",
    )
    target_language_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.languages.id"),
        index=True,
        comment="Language expected in quiz answers",
    )
    selection_mode: Mapped[str | None] = mapped_column(
        String, comment="Strategy used to select questions"
    )
    requested_question_count: Mapped[int | None] = mapped_column(
        comment="Number of questions requested"
    )
    actual_question_count: Mapped[int | None] = mapped_column(
        comment="Number of questions generated"
    )
    configuration: Mapped[dict | None] = mapped_column(
        JSON, comment="Snapshot of the quiz configuration"
    )
    questions: Mapped[list[dict] | None] = mapped_column(
        JSON, comment="Immutable snapshot of generated questions"
    )
    client_type: Mapped[str | None] = mapped_column(
        String, comment="Interface that created the quiz"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="Time the quiz was completed"
    )
    correct_count: Mapped[int | None] = mapped_column(
        comment="Number of fully correct answers"
    )
    score_percentage: Mapped[float | None] = mapped_column(
        Float, comment="Final score expressed as a percentage"
    )
    advice: Mapped[dict | None] = mapped_column(
        JSON, comment="Structured learning advice for the result"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the quiz session was created",
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    __table_args__ = {"schema": SPANGGLISH_SCHEMA}


class QuizAttempt(Base):
    """A server-evaluated answer submitted after a quiz finishes."""

    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(primary_key=True, comment="Quiz attempt identifier")
    session_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Quiz session containing the attempt",
    )
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Vocabulary tested by the question",
    )
    question_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Stable question identifier in the quiz snapshot",
    )
    answer: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="Answer submitted by the user"
    )
    expected_answers: Mapped[list[str] | dict] = mapped_column(
        JSON, nullable=False, comment="Accepted answers used for evaluation"
    )
    answered_correctly: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
        comment="Whether the submitted answer was correct",
    )
    score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Numeric score awarded for the answer"
    )
    response_time_ms: Mapped[int | None] = mapped_column(
        comment="Answer time in milliseconds"
    )
    feedback: Mapped[str | None] = mapped_column(
        String, comment="Optional feedback for the submitted answer"
    )
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Time the answer was recorded",
    )
    session: Mapped[QuizSession] = relationship(back_populates="attempts")
    vocabulary: Mapped[Vocabulary] = relationship(back_populates="attempts")
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_quiz_question_attempt"),
        {"schema": SPANGGLISH_SCHEMA},
    )
