import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.configs.db import Base



# =========================
# Language
# =========================

class Language(Base):
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

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_language_name_user"),
        UniqueConstraint("code", "user_id", name="uq_language_code_user"),
    )


# =========================
# Vocabulary Type
# =========================

class VocabularyType(Base):
    __tablename__ = "vocabulary_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    vocabulary: Mapped[list["Vocabulary"]] = relationship(
        "Vocabulary",
        back_populates="vocabulary_type",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_vocabularytype_name_user"),
    )


# =========================
# Category
# =========================

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    vocabularies: Mapped[list["Vocabulary"]] = relationship(
        "Vocabulary",
        secondary="vocabulary_categories",
        back_populates="categories"
    )

    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_category_name_user"),
    )


# =========================
# Chapter
# =========================

class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    vocabulary: Mapped[list["Vocabulary"]] = relationship(
        "Vocabulary",
        back_populates="chapter"
    )

    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_chapter_name_user"),
    )


# =========================
# Vocabulary
# =========================

class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    text: Mapped[str] = mapped_column(String, nullable=False, index=True)

    language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    vocabulary_type_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), index=True
    )

    verb_conjugations: Mapped[list["VerbConjugation"]] = relationship(
        "VerbConjugation",
        back_populates="vocabulary",
        cascade="all, delete-orphan"
    )

    translations: Mapped[list["Translation"]] = relationship(
        "Translation",
        back_populates="vocabulary",
        cascade="all, delete-orphan"
    )

    examples: Mapped[list["VocabularyExamples"]] = relationship(
        "VocabularyExamples",
        back_populates="vocabulary",
        cascade="all, delete-orphan"
    )

    attempts: Mapped[list["QuizAttempt"]] = relationship(
        "QuizAttempt",
        back_populates="vocabulary",
        cascade="all, delete-orphan"
    )

    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="vocabulary")

    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary="vocabulary_categories",
        back_populates="vocabularies"
    )

    vocabulary_type: Mapped["VocabularyType"] = relationship(
        "VocabularyType",
        back_populates="vocabulary"
    )

    __table_args__ = (
        UniqueConstraint("text", "language_id", "user_id",
                         name="uq_vocabulary_text_language_user"),
    )


# =========================
# Vocabulary ↔ Category (M2M)
# =========================

class VocabularyCategory(Base):
    __tablename__ = "vocabulary_categories"

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"),
        primary_key=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


# =========================
# Verb Conjugation
# =========================

class VerbConjugation(Base):
    __tablename__ = "verb_conjugations"

    id: Mapped[int] = mapped_column(primary_key=True)

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    conjugation: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    vocabulary: Mapped["Vocabulary"] = relationship("Vocabulary", back_populates="verb_conjugations")


# =========================
# Vocabulary Examples
# =========================

class VocabularyExamples(Base):
    __tablename__ = "vocabulary_examples"

    id: Mapped[int] = mapped_column(primary_key=True)

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    ai_agent_id: Mapped[int] = mapped_column(
        ForeignKey("ai_agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    example: Mapped[str] = mapped_column(String, nullable=False)
    translation: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    vocabulary = relationship("Vocabulary", back_populates="examples")
    ai_agent = relationship("AIAgent", back_populates="examples")

# =========================
# Translation
# =========================

class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(primary_key=True)

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    translation: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    vocabulary = relationship("Vocabulary", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("vocabulary_id", "translation"),
    )


# =========================
# Quiz
# =========================

class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    attempts = relationship(
        "QuizAttempt",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    answer: Mapped[str] = mapped_column(String, nullable=False)
    answered_correctly: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    session = relationship("QuizSession", back_populates="attempts")
    vocabulary = relationship("Vocabulary", back_populates="attempts")