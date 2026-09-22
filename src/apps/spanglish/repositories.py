"""SQLAlchemy persistence operations for the Spanglish application."""

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from src.apps.spanglish import models
from src.enums import QuizSelectionMode


class SpanglishRepository:
    """Keep database queries separate from HTTP and quiz rules."""

    def __init__(self, db: Session):
        """Store the request-scoped SQLAlchemy session."""
        self.db = db

    def ensure_user_references(self, user_id) -> None:
        """Copy reference defaults from the first account into a new account."""
        for table, fields in (
            ("languages", "name, code"),
            ("categories", "name"),
            ("chapters", "name"),
        ):
            self.db.execute(
                text(
                    f"INSERT INTO spanglish.{table} ({fields}, user_id) "
                    f"SELECT {fields}, :user_id FROM spanglish.{table} "
                    "WHERE user_id = ("
                    "SELECT id FROM public.users ORDER BY created_at, id LIMIT 1"
                    ") AND user_id <> :user_id ON CONFLICT DO NOTHING"
                ),
                {"user_id": user_id},
            )
        self.db.commit()

    def list_languages(self, user_id) -> list[models.Language]:
        """Return languages ordered for stable interface controls."""
        return list(
            self.db.scalars(
                select(models.Language)
                .where(models.Language.user_id == user_id)
                .order_by(models.Language.name)
            )
        )

    def list_categories(self, user_id) -> list[models.Category]:
        """Return categories ordered for stable cards and menus."""
        return list(
            self.db.scalars(
                select(models.Category)
                .where(models.Category.user_id == user_id)
                .order_by(models.Category.name)
            )
        )

    def list_chapters(self, user_id) -> list[models.Chapter]:
        """Return optional lesson chapters in stable display order."""
        return list(
            self.db.scalars(
                select(models.Chapter)
                .where(models.Chapter.user_id == user_id)
                .order_by(models.Chapter.name)
            )
        )

    def create_language(self, name: str, code: str, user_id) -> models.Language:
        """Persist a language for one authenticated user."""
        language = models.Language(
            name=name.strip(), code=code.strip().lower(), user_id=user_id
        )
        self.db.add(language)
        self.db.commit()
        self.db.refresh(language)
        return language

    def create_category(self, name: str, user_id) -> models.Category:
        """Persist a quiz and vocabulary topic."""
        category = models.Category(name=name.strip(), user_id=user_id)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def create_chapter(self, name: str, user_id) -> models.Chapter:
        """Persist an optional vocabulary and quiz chapter."""
        chapter = models.Chapter(name=name.strip(), user_id=user_id)
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)
        return chapter

    def list_artists(self, user_id) -> list[models.Artist]:
        """List only artists owned by the authenticated learner."""
        return list(
            self.db.scalars(
                select(models.Artist)
                .where(models.Artist.user_id == user_id)
                .order_by(models.Artist.name)
            )
        )

    def create_artist(self, name: str, user_id) -> models.Artist:
        """Create a performer owned by the authenticated learner."""
        artist = models.Artist(name=name.strip(), user_id=user_id)
        self.db.add(artist)
        self.db.commit()
        self.db.refresh(artist)
        return artist

    def get_artist(self, artist_id: int, user_id) -> models.Artist | None:
        """Find an artist only within the learner's collection."""
        return self.db.scalars(
            select(models.Artist).where(
                models.Artist.id == artist_id, models.Artist.user_id == user_id
            )
        ).first()

    def list_songs(self, user_id, artist_id: int | None = None) -> list[models.Song]:
        """List the learner's songs, optionally for one artist."""
        query = (
            select(models.Song)
            .join(models.Song.artist)
            .options(selectinload(models.Song.artist))
            .where(models.Artist.user_id == user_id)
        )
        if artist_id is not None:
            query = query.where(models.Song.artist_id == artist_id)
        return list(self.db.scalars(query.order_by(models.Song.title)))

    def create_song(self, title: str, artist_id: int, user_id) -> models.Song:
        """Create a user-owned title under a user-owned artist."""
        song = models.Song(title=title.strip(), artist_id=artist_id)
        self.db.add(song)
        self.db.commit()
        return self.get_song(song.id, user_id)  # type: ignore[return-value]

    def get_song(self, song_id: int, user_id) -> models.Song | None:
        """Find one song within the authenticated learner's collection."""
        return self.db.scalars(
            select(models.Song)
            .join(models.Song.artist)
            .options(selectinload(models.Song.artist))
            .where(models.Song.id == song_id, models.Artist.user_id == user_id)
        ).first()

    def get_language(self, language_id: int, user_id) -> models.Language | None:
        """Return one language by primary key."""
        return self.db.scalars(
            select(models.Language).where(
                models.Language.id == language_id,
                models.Language.user_id == user_id,
            )
        ).first()

    def get_chapter(self, chapter_id: int, user_id) -> models.Chapter | None:
        """Return one chapter by primary key."""
        return self.db.scalars(
            select(models.Chapter).where(
                models.Chapter.id == chapter_id,
                models.Chapter.user_id == user_id,
            )
        ).first()

    def get_chapters(self, chapter_ids: list[int], user_id) -> list[models.Chapter]:
        """Return all chapters matching the provided identifiers."""
        if not chapter_ids:
            return []
        return list(
            self.db.scalars(
                select(models.Chapter).where(
                    models.Chapter.id.in_(chapter_ids),
                    models.Chapter.user_id == user_id,
                )
            )
        )

    def get_categories(self, category_ids: list[int], user_id) -> list[models.Category]:
        """Return all categories matching the provided identifiers."""
        if not category_ids:
            return []
        return list(
            self.db.scalars(
                select(models.Category).where(
                    models.Category.id.in_(category_ids),
                    models.Category.user_id == user_id,
                )
            )
        )

    def create_vocabulary(
        self,
        *,
        text: str,
        user_id,
        language_id: int,
        chapter_id: int | None,
        song_id: int | None,
        categories: list[models.Category],
        translations: list[dict],
        conjugations: list[dict],
    ) -> models.Vocabulary:
        """Persist one complete vocabulary aggregate in a transaction."""
        vocabulary = models.Vocabulary(
            text=text.strip(),
            user_id=user_id,
            language_id=language_id,
            chapter_id=chapter_id,
            song_id=song_id,
            categories=categories,
            translations=[
                models.Translation(
                    translation=item["text"].strip(),
                    language_id=item["language_id"],
                )
                for item in translations
            ],
            verb_conjugations=[models.VerbConjugation(**item) for item in conjugations],
        )
        self.db.add(vocabulary)
        self.db.commit()
        return self.get_vocabulary(vocabulary.id, user_id)  # type: ignore[return-value]

    def get_vocabulary(self, vocabulary_id: int, user_id) -> models.Vocabulary | None:
        """Return one eagerly loaded vocabulary card."""
        query = self._vocabulary_query().where(
            models.Vocabulary.id == vocabulary_id, models.Vocabulary.user_id == user_id
        )
        return self.db.scalars(query).unique().first()

    def update_vocabulary(
        self,
        vocabulary: models.Vocabulary,
        *,
        text: str,
        language_id: int,
        chapter_id: int | None,
        song_id: int | None,
        categories: list[models.Category],
        translations: list[dict],
        conjugations: list[dict],
    ) -> models.Vocabulary:
        """Replace a vocabulary aggregate and its client-managed children."""
        vocabulary.text = text.strip()
        vocabulary.language_id = language_id
        vocabulary.chapter_id = chapter_id
        vocabulary.song_id = song_id
        vocabulary.categories = categories
        vocabulary.translations = [
            models.Translation(
                translation=item["text"].strip(),
                language_id=item["language_id"],
            )
            for item in translations
        ]
        vocabulary.verb_conjugations = [
            models.VerbConjugation(**item) for item in conjugations
        ]
        self.db.commit()
        return self.get_vocabulary(vocabulary.id, vocabulary.user_id)  # type: ignore[return-value]

    def delete_vocabulary(self, vocabulary: models.Vocabulary) -> None:
        """Delete a vocabulary aggregate and cascading child rows."""
        self.db.delete(vocabulary)
        self.db.commit()

    def list_conjugations(
        self, vocabulary_id: int, user_id
    ) -> list[models.VerbConjugation]:
        """Return all conjugations for a vocabulary item in display order."""
        query = (
            select(models.VerbConjugation)
            .where(
                models.VerbConjugation.vocabulary_id == vocabulary_id,
            )
            .order_by(
                models.VerbConjugation.tense,
                models.VerbConjugation.mood,
                models.VerbConjugation.id,
            )
        )
        return list(self.db.scalars(query))

    def get_conjugation(
        self, vocabulary_id: int, conjugation_id: int, user_id
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
        user_id,
        language_id: int | None,
        category_id: int | None,
        chapter_id: int | None,
        search: str | None,
        randomize: bool = False,
    ) -> tuple[list[models.Vocabulary], int]:
        """Return a filtered and paginated vocabulary collection with total count."""
        filters = [models.Vocabulary.user_id == user_id]
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

    def count_vocabulary_by_category(self, user_id) -> dict[int, int]:
        """Count vocabulary records per category for quiz builder cards."""
        query = (
            select(models.VocabularyCategory.category_id, func.count())
            .join(
                models.Vocabulary,
                models.Vocabulary.id == models.VocabularyCategory.vocabulary_id,
            )
            .where(models.Vocabulary.user_id == user_id)
            .group_by(models.VocabularyCategory.category_id)
        )
        return {category_id: count for category_id, count in self.db.execute(query)}

    def select_quiz_vocabulary(
        self,
        *,
        source_language_id: int,
        user_id,
        target_language_id: int,
        category_ids: list[int],
        chapter_ids: list[int],
        limit: int,
        selection_mode: QuizSelectionMode,
    ) -> list[models.Vocabulary]:
        """Select eligible vocabulary using the requested filters and ordering."""
        query = self._vocabulary_query().where(
            models.Vocabulary.user_id == user_id,
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
            ),
        )
        if category_ids:
            query = query.where(
                models.Vocabulary.categories.any(models.Category.id.in_(category_ids))
            )
        if chapter_ids:
            query = query.where(models.Vocabulary.chapter_id.in_(chapter_ids))
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

    def list_quiz_results(self, user_id, limit: int) -> list[models.QuizSession]:
        """Return a user's most recently completed quizzes, newest first."""
        query = (
            select(models.QuizSession)
            .where(
                models.QuizSession.user_id == user_id,
                models.QuizSession.completed_at.is_not(None),
            )
            .order_by(models.QuizSession.completed_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(query))

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
            selectinload(models.Vocabulary.chapter),
            selectinload(models.Vocabulary.song).selectinload(models.Song.artist),
            selectinload(models.Vocabulary.categories),
            selectinload(models.Vocabulary.translations),
            selectinload(models.Vocabulary.verb_conjugations),
            selectinload(models.Vocabulary.examples),
        )
