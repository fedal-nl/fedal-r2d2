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
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    __table_args__ = (
        UniqueConstraint("name", name="uq_language_name"),
        UniqueConstraint("code", name="uq_language_code"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class VocabularyType(Base):
    """The shape of learning content, such as a word or phrase."""

    __tablename__ = "vocabulary_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    vocabulary: Mapped[list["Vocabulary"]] = relationship(
        back_populates="vocabulary_type"
    )
    __table_args__ = (
        UniqueConstraint("name", name="uq_vocabularytype_name"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Category(Base):
    """A topic used to browse vocabulary and configure quizzes."""

    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    vocabularies: Mapped[list["Vocabulary"]] = relationship(
        secondary="spanglish.vocabulary_categories", back_populates="categories"
    )
    __table_args__ = (
        UniqueConstraint("name", name="uq_category_name"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Chapter(Base):
    """An optional collection that groups vocabulary into a lesson."""

    __tablename__ = "chapters"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    vocabulary: Mapped[list["Vocabulary"]] = relationship(back_populates="chapter")
    __table_args__ = (
        UniqueConstraint("name", name="uq_chapter_name"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class Vocabulary(Base):
    """A source-language term with translations and learning metadata."""

    __tablename__ = "vocabulary"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(String, nullable=False, index=True)
    language_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.languages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vocabulary_type_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.chapters.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )
    language: Mapped[Language] = relationship()
    vocabulary_type: Mapped[VocabularyType] = relationship(back_populates="vocabulary")
    chapter: Mapped[Chapter | None] = relationship(back_populates="vocabulary")
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
        UniqueConstraint("text", "language_id", name="uq_vocabulary_text_language"),
        {"schema": SPANGGLISH_SCHEMA},
    )


class VocabularyCategory(Base):
    """Association between vocabulary and one or more topics."""

    __tablename__ = "vocabulary_categories"
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.categories.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    __table_args__ = {"schema": SPANGGLISH_SCHEMA}


class VerbConjugation(Base):
    """A structured verb form that can become a quiz item."""

    __tablename__ = "verb_conjugations"
    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tense: Mapped[str] = mapped_column(String, nullable=False, default="present")
    mood: Mapped[str] = mapped_column(String, nullable=False, default="indicative")
    pronoun: Mapped[str] = mapped_column(String, nullable=False)
    form: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
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
    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai.ai_agents.id", ondelete="SET NULL"), index=True
    )
    example: Mapped[str] = mapped_column(String, nullable=False)
    translation: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    vocabulary: Mapped[Vocabulary] = relationship(back_populates="examples")
    __table_args__ = {"schema": SPANGGLISH_SCHEMA}


VocabularyExamples = VocabularyExample


class Translation(Base):
    """One accepted translation for a vocabulary item."""

    __tablename__ = "translations"
    id: Mapped[int] = mapped_column(primary_key=True)
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.languages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    translation: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
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
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_language_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.languages.id"), index=True
    )
    target_language_id: Mapped[int | None] = mapped_column(
        ForeignKey("spanglish.languages.id"), index=True
    )
    selection_mode: Mapped[str | None] = mapped_column(String)
    requested_question_count: Mapped[int | None] = mapped_column()
    actual_question_count: Mapped[int | None] = mapped_column()
    configuration: Mapped[dict | None] = mapped_column(JSON)
    questions: Mapped[list[dict] | None] = mapped_column(JSON)
    client_type: Mapped[str | None] = mapped_column(String)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correct_count: Mapped[int | None] = mapped_column()
    score_percentage: Mapped[float | None] = mapped_column(Float)
    advice: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    __table_args__ = {"schema": SPANGGLISH_SCHEMA}


class QuizAttempt(Base):
    """A server-evaluated answer submitted after a quiz finishes."""

    __tablename__ = "quiz_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("spanglish.vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(String, nullable=False)
    answer: Mapped[dict] = mapped_column(JSON, nullable=False)
    expected_answers: Mapped[list[str] | dict] = mapped_column(JSON, nullable=False)
    answered_correctly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column()
    feedback: Mapped[str | None] = mapped_column(String)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    session: Mapped[QuizSession] = relationship(back_populates="attempts")
    vocabulary: Mapped[Vocabulary] = relationship(back_populates="attempts")
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_quiz_question_attempt"),
        {"schema": SPANGGLISH_SCHEMA},
    )
