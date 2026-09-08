"""SQLAlchemy persistence operations for the Spanglish application."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.apps.spanglish import models
from src.enums import QuizSelectionMode


class SpanglishRepository:
    """Keep database queries separate from HTTP and quiz rules."""

    def __init__(self, db: Session):
        """Store the request-scoped SQLAlchemy session."""
        self.db = db

    def list_languages(self) -> list[models.Language]:
        """Return languages ordered for stable interface controls."""
        return list(
            self.db.scalars(select(models.Language).order_by(models.Language.name))
        )

    def list_categories(self) -> list[models.Category]:
        """Return categories ordered for stable cards and menus."""
        return list(
            self.db.scalars(select(models.Category).order_by(models.Category.name))
        )

    def list_vocabulary_types(self) -> list[models.VocabularyType]:
        """Return vocabulary types ordered by display name."""
        return list(
            self.db.scalars(
                select(models.VocabularyType).order_by(models.VocabularyType.name)
            )
        )

    def list_chapters(self) -> list[models.Chapter]:
        """Return optional lesson chapters in stable display order."""
        return list(
            self.db.scalars(select(models.Chapter).order_by(models.Chapter.name))
        )

    def create_language(self, name: str, code: str) -> models.Language:
        """Persist a globally available language."""
        language = models.Language(name=name.strip(), code=code.strip().lower())
        self.db.add(language)
        self.db.commit()
        self.db.refresh(language)
        return language

    def create_category(self, name: str) -> models.Category:
        """Persist a quiz and vocabulary topic."""
        category = models.Category(name=name.strip())
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def create_chapter(self, name: str) -> models.Chapter:
        """Persist an optional vocabulary and quiz chapter."""
        chapter = models.Chapter(name=name.strip())
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)
        return chapter

    def create_vocabulary_type(self, name: str) -> models.VocabularyType:
        """Persist a vocabulary content type."""
        vocabulary_type = models.VocabularyType(name=name.strip())
        self.db.add(vocabulary_type)
        self.db.commit()
        self.db.refresh(vocabulary_type)
        return vocabulary_type

    def get_language(self, language_id: int) -> models.Language | None:
        """Return one language by primary key."""
        return self.db.get(models.Language, language_id)

    def get_vocabulary_type(
        self, vocabulary_type_id: int
    ) -> models.VocabularyType | None:
        """Return one vocabulary type by primary key."""
        return self.db.get(models.VocabularyType, vocabulary_type_id)

    def get_chapter(self, chapter_id: int) -> models.Chapter | None:
        """Return one chapter by primary key."""
        return self.db.get(models.Chapter, chapter_id)

    def get_chapters(self, chapter_ids: list[int]) -> list[models.Chapter]:
        """Return all chapters matching the provided identifiers."""
        if not chapter_ids:
            return []
        return list(
            self.db.scalars(
                select(models.Chapter).where(models.Chapter.id.in_(chapter_ids))
            )
        )

    def get_categories(self, category_ids: list[int]) -> list[models.Category]:
        """Return all categories matching the provided identifiers."""
        if not category_ids:
            return []
        return list(
            self.db.scalars(
                select(models.Category).where(models.Category.id.in_(category_ids))
            )
        )

    def create_vocabulary(
        self,
        *,
        text: str,
        language_id: int,
        vocabulary_type_id: int,
        chapter_id: int | None,
        categories: list[models.Category],
        translations: list[dict],
        conjugations: list[dict],
    ) -> models.Vocabulary:
        """Persist one complete vocabulary aggregate in a transaction."""
        vocabulary = models.Vocabulary(
            text=text.strip(),
            language_id=language_id,
            vocabulary_type_id=vocabulary_type_id,
            chapter_id=chapter_id,
            categories=categories,
            translations=[
                models.Translation(
                    translation=item["text"].strip(), language_id=item["language_id"]
                )
                for item in translations
            ],
            verb_conjugations=[models.VerbConjugation(**item) for item in conjugations],
        )
        self.db.add(vocabulary)
        self.db.commit()
        return self.get_vocabulary(vocabulary.id)  # type: ignore[return-value]

    def get_vocabulary(self, vocabulary_id: int) -> models.Vocabulary | None:
        """Return one eagerly loaded vocabulary card."""
        query = self._vocabulary_query().where(models.Vocabulary.id == vocabulary_id)
        return self.db.scalars(query).unique().first()

    def update_vocabulary(
        self,
        vocabulary: models.Vocabulary,
        *,
        text: str,
        language_id: int,
        vocabulary_type_id: int,
        chapter_id: int | None,
        categories: list[models.Category],
        translations: list[dict],
        conjugations: list[dict],
    ) -> models.Vocabulary:
        """Replace a vocabulary aggregate and its client-managed children."""
        vocabulary.text = text.strip()
        vocabulary.language_id = language_id
        vocabulary.vocabulary_type_id = vocabulary_type_id
        vocabulary.chapter_id = chapter_id
        vocabulary.categories = categories
        vocabulary.translations = [
            models.Translation(
                translation=item["text"].strip(), language_id=item["language_id"]
            )
            for item in translations
        ]
        vocabulary.verb_conjugations = [
            models.VerbConjugation(**item) for item in conjugations
        ]
        self.db.commit()
        return self.get_vocabulary(vocabulary.id)  # type: ignore[return-value]

    def delete_vocabulary(self, vocabulary: models.Vocabulary) -> None:
        """Delete a vocabulary aggregate and cascading child rows."""
        self.db.delete(vocabulary)
        self.db.commit()

    def list_conjugations(self, vocabulary_id: int) -> list[models.VerbConjugation]:
        """Return all conjugations for a vocabulary item in display order."""
        query = (
            select(models.VerbConjugation)
            .where(models.VerbConjugation.vocabulary_id == vocabulary_id)
            .order_by(
                models.VerbConjugation.tense,
                models.VerbConjugation.mood,
                models.VerbConjugation.id,
            )
        )
        return list(self.db.scalars(query))

    def get_conjugation(
        self, vocabulary_id: int, conjugation_id: int
    ) -> models.VerbConjugation | None:
        """Return a conjugation only when it belongs to the vocabulary item."""
        query = select(models.VerbConjugation).where(
            models.VerbConjugation.id == conjugation_id,
            models.VerbConjugation.vocabulary_id == vocabulary_id,
        )
        return self.db.scalars(query).first()

    def create_conjugation(
        self, vocabulary_id: int, **values: str
    ) -> models.VerbConjugation:
        """Persist a new structured conjugation for existing vocabulary."""
        conjugation = models.VerbConjugation(vocabulary_id=vocabulary_id, **values)
        self.db.add(conjugation)
        self.db.commit()
        self.db.refresh(conjugation)
        return conjugation

    def update_conjugation(
        self, conjugation: models.VerbConjugation, **values: str
    ) -> models.VerbConjugation:
        """Replace the editable fields of a persisted conjugation."""
        for field, value in values.items():
            setattr(conjugation, field, value)
        self.db.commit()
        self.db.refresh(conjugation)
        return conjugation

    def delete_conjugation(self, conjugation: models.VerbConjugation) -> None:
        """Delete one conjugation from its vocabulary item."""
        self.db.delete(conjugation)
        self.db.commit()

    def list_vocabulary(
        self,
        *,
        page: int,
        page_size: int,
        language_id: int | None,
        category_id: int | None,
        chapter_id: int | None,
        search: str | None,
        randomize: bool = False,
    ) -> tuple[list[models.Vocabulary], int]:
        """Return a filtered and paginated vocabulary collection with total count."""
        filters = []
        if language_id is not None:
            filters.append(models.Vocabulary.language_id == language_id)
        if search:
            filters.append(models.Vocabulary.text.ilike(f"%{search.strip()}%"))
        if category_id is not None:
            filters.append(
                models.Vocabulary.categories.any(models.Category.id == category_id)
            )
        if chapter_id is not None:
            filters.append(models.Vocabulary.chapter_id == chapter_id)
        total = (
            self.db.scalar(
                select(func.count()).select_from(models.Vocabulary).where(*filters)
            )
            or 0
        )
        ordering = func.random() if randomize else models.Vocabulary.text
        query = (
            self._vocabulary_query()
            .where(*filters)
            .order_by(ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(query).unique()), total

    def count_vocabulary_by_category(self) -> dict[int, int]:
        """Count vocabulary records per category for quiz builder cards."""
        query = select(models.VocabularyCategory.category_id, func.count()).group_by(
            models.VocabularyCategory.category_id
        )
        return {category_id: count for category_id, count in self.db.execute(query)}

    def select_quiz_vocabulary(
        self,
        *,
        source_language_id: int,
        target_language_id: int,
        category_ids: list[int],
        chapter_ids: list[int],
        vocabulary_type_ids: list[int],
        limit: int,
        selection_mode: QuizSelectionMode,
    ) -> list[models.Vocabulary]:
        """Select eligible vocabulary using the requested filters and ordering."""
        query = self._vocabulary_query().where(
            or_(
                and_(
                    models.Vocabulary.language_id == source_language_id,
                    models.Vocabulary.translations.any(
                        models.Translation.language_id == target_language_id
                    ),
                ),
                and_(
                    models.Vocabulary.language_id == target_language_id,
                    models.Vocabulary.translations.any(
                        models.Translation.language_id == source_language_id
                    ),
                ),
            )
        )
        if category_ids:
            query = query.where(
                models.Vocabulary.categories.any(models.Category.id.in_(category_ids))
            )
        if chapter_ids:
            query = query.where(models.Vocabulary.chapter_id.in_(chapter_ids))
        if vocabulary_type_ids:
            query = query.where(
                models.Vocabulary.vocabulary_type_id.in_(vocabulary_type_ids)
            )
        ordering = (
            func.random()
            if selection_mode == QuizSelectionMode.RANDOM
            else models.Vocabulary.text
        )
        return list(self.db.scalars(query.order_by(ordering).limit(limit)).unique())

    def create_quiz(self, **values) -> models.QuizSession:
        """Persist the immutable question snapshot used for final verification."""
        quiz = models.QuizSession(**values)
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    def get_quiz(self, quiz_id: int, user_id) -> models.QuizSession | None:
        """Return a quiz only when it belongs to the authenticated user."""
        query = (
            select(models.QuizSession)
            .options(selectinload(models.QuizSession.attempts))
            .where(
                models.QuizSession.id == quiz_id,
                models.QuizSession.user_id == user_id,
            )
        )
        return self.db.scalars(query).first()

    def save_result(
        self, quiz: models.QuizSession, attempts: list[models.QuizAttempt]
    ) -> models.QuizSession:
        """Persist evaluated attempts and final aggregate values atomically."""
        quiz.attempts.extend(attempts)
        self.db.commit()
        self.db.refresh(quiz)
        return quiz

    @staticmethod
    def _vocabulary_query():
        """Build the eager-loading query shared by vocabulary reads."""
        return select(models.Vocabulary).options(
            selectinload(models.Vocabulary.language),
            selectinload(models.Vocabulary.vocabulary_type),
            selectinload(models.Vocabulary.chapter),
            selectinload(models.Vocabulary.categories),
            selectinload(models.Vocabulary.translations),
            selectinload(models.Vocabulary.verb_conjugations),
        )
