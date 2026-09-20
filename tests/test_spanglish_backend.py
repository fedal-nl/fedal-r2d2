"""Unit tests for Spanglish services, repositories, and route wrappers."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.apps.spanglish import models, routers, schemas
from src.apps.spanglish.repositories import SpanglishRepository
from src.apps.spanglish.services import SpanglishService
from src.enums import QuizQuestionType, QuizSelectionMode

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeScalars:
    """Emulate the small ScalarResult surface used by the repository."""

    def __init__(self, values):
        self.values = list(values)

    def __iter__(self):
        return iter(self.values)

    def unique(self):
        return self

    def first(self):
        return self.values[0] if self.values else None


def reference_data():
    """Build reusable model-like values without a database."""
    es = SimpleNamespace(id=1, name="Spanish", code="es")
    en = SimpleNamespace(id=2, name="English", code="en")
    category = SimpleNamespace(id=3, name="Animals")
    chapter = SimpleNamespace(id=5, name="Chapter 1")
    return es, en, category, chapter


class FakeRepository:
    """Provide configurable persistence behavior to service unit tests."""

    def __init__(self):
        self.es, self.en, self.category, self.chapter = reference_data()
        self.languages = {1: self.es, 2: self.en}
        self.categories = [self.category]
        self.rows = []
        self.quiz = None
        self.vocabulary = SimpleNamespace(id=7)
        self.conjugation = SimpleNamespace(
            id=8,
            vocabulary_id=7,
            tense="present",
            mood="indicative",
            pronoun="yo",
            form="hablo",
        )
        self.db = MagicMock()

    def ensure_user_references(self, user_id):
        """The fake already exposes one user's reference fixtures."""
        assert user_id == USER_ID

    def count_vocabulary_by_category(self, user_id):
        return {3: 2}

    def list_categories(self, user_id):
        return self.categories

    def list_languages(self, user_id):
        return list(self.languages.values())

    def list_chapters(self, user_id):
        return [self.chapter]

    def get_language(self, value, user_id):
        return self.languages.get(value)

    def get_chapter(self, value, user_id):
        return self.chapter if value == 5 else None

    def get_chapters(self, values, user_id):
        return [self.chapter] if values == [5] else []

    def get_categories(self, values, user_id):
        return self.categories if values == [3] else []

    def get_song(self, song_id, user_id):
        if song_id == 12 and user_id == USER_ID:
            return SimpleNamespace(id=12, user_id=USER_ID)
        return None

    def create_vocabulary(self, **values):
        return values

    def update_vocabulary(self, vocabulary, **values):
        for field, value in values.items():
            setattr(vocabulary, field, value)
        return vocabulary

    def delete_vocabulary(self, vocabulary):
        self.vocabulary = None

    def get_vocabulary(self, value, user_id):
        return self.vocabulary if value == 7 else None

    def list_conjugations(self, value, user_id):
        return [self.conjugation] if value == 7 else []

    def get_conjugation(self, vocabulary_id, conjugation_id, user_id):
        if vocabulary_id == 7 and conjugation_id == 8:
            return self.conjugation
        return None

    def create_conjugation(self, vocabulary_id, user_id, **values):
        return SimpleNamespace(id=9, vocabulary_id=vocabulary_id, **values)

    def update_conjugation(self, conjugation, **values):
        for field, value in values.items():
            setattr(conjugation, field, value)
        return conjugation

    def delete_conjugation(self, conjugation):
        self.conjugation = None

    def select_quiz_vocabulary(self, **values):
        return self.rows

    def create_quiz(self, **values):
        self.quiz = SimpleNamespace(
            id=9,
            created_at=datetime.now(UTC),
            completed_at=None,
            correct_count=None,
            score_percentage=None,
            advice=None,
            attempts=[],
            **values,
        )
        return self.quiz

    def get_quiz(self, quiz_id, user_id):
        return self.quiz if quiz_id == 9 and user_id == USER_ID else None

    def list_quiz_results(self, user_id, limit):
        if user_id != USER_ID or self.quiz is None:
            return []
        return [self.quiz][:limit]

    def save_result(self, quiz, attempts):
        quiz.attempts = attempts
        return quiz


def vocabulary_row(conjugations=True):
    """Create a Spanish vocabulary row eligible for an English quiz."""
    return SimpleNamespace(
        id=7,
        text="hablar",
        language_id=1,
        categories=[SimpleNamespace(id=3)],
        translations=[SimpleNamespace(language_id=2, translation="to speak")],
        verb_conjugations=(
            [SimpleNamespace(pronoun="yo", form="hablo")] if conjugations else []
        ),
    )


def test_service_options_and_vocabulary_validation() -> None:
    """Build quiz controls and validate every vocabulary reference."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    options = service.get_quiz_options(USER_ID)
    assert options.categories[0].available_questions == 2
    assert options.chapters[0].name == "Chapter 1"
    payload = schemas.VocabularyCreate(
        text="perro",
        language_id=1,
        chapter_id=5,
        category_ids=[3],
        translations=[{"language_id": 2, "text": "dog"}],
    )
    assert service.create_vocabulary(payload, USER_ID)["text"] == "perro"

    repository.languages.pop(1)
    with pytest.raises(HTTPException, match="Source language"):
        service.create_vocabulary(payload, USER_ID)
    repository.languages[1] = repository.es
    payload.chapter_id = 99
    with pytest.raises(HTTPException, match="Chapter"):
        service.create_vocabulary(payload, USER_ID)
    payload.chapter_id = 5
    payload.category_ids = [99]
    with pytest.raises(HTTPException, match="categories"):
        service.create_vocabulary(payload, USER_ID)
    payload.category_ids = [3]
    payload.translations[0].language_id = 99
    with pytest.raises(HTTPException, match="Translation language"):
        service.create_vocabulary(payload, USER_ID)


def test_service_translates_integrity_error_to_conflict() -> None:
    """Return a useful conflict when vocabulary uniqueness is violated."""
    repository = FakeRepository()
    repository.create_vocabulary = MagicMock(
        side_effect=IntegrityError("x", {}, Exception())
    )
    payload = schemas.VocabularyCreate(
        text="perro",
        language_id=1,
        chapter_id=5,
        translations=[{"language_id": 2, "text": "dog"}],
    )
    with pytest.raises(HTTPException) as error:
        SpanglishService(repository).create_vocabulary(payload, USER_ID)
    assert error.value.status_code == 409
    repository.db.rollback.assert_called_once()


def test_song_category_requires_a_song_owned_by_the_user() -> None:
    """Reject missing or foreign song links before persisting vocabulary."""
    repository = FakeRepository()
    repository.categories = [SimpleNamespace(id=3, name="Songs")]
    service = SpanglishService(repository)
    payload = schemas.VocabularyCreate(
        text="letra",
        language_id=1,
        category_ids=[3],
        translations=[{"language_id": 2, "text": "lyric"}],
    )
    with pytest.raises(HTTPException) as missing:
        service.create_vocabulary(payload, USER_ID)
    assert missing.value.status_code == 422
    payload.song_id = 13
    with pytest.raises(HTTPException) as foreign:
        service.create_vocabulary(payload, USER_ID)
    assert foreign.value.status_code == 404
    payload.song_id = 12
    assert service.create_vocabulary(payload, USER_ID)["song_id"] == 12


def test_cross_user_vocabulary_id_is_not_found() -> None:
    """Do not permit one authenticated learner to modify another's vocabulary."""
    repository = FakeRepository()
    repository.get_vocabulary = lambda vocabulary_id, user_id: (
        repository.vocabulary if user_id == USER_ID and vocabulary_id == 7 else None
    )
    with pytest.raises(HTTPException) as error:
        SpanglishService(repository).delete_vocabulary(
            7, UUID("22222222-2222-2222-2222-222222222222")
        )
    assert error.value.status_code == 404
    assert repository.vocabulary is not None


def test_conjugation_service_crud_and_not_found() -> None:
    """Create, list, replace, and delete forms while enforcing ownership."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    create = schemas.ConjugationCreate(pronoun="tú", form="hablas")
    update = schemas.ConjugationUpdate(
        tense="present", mood="indicative", pronoun="yo", form="hablé"
    )
    assert service.list_conjugations(7, USER_ID)[0].form == "hablo"
    assert service.create_conjugation(7, create, USER_ID).form == "hablas"
    assert service.update_conjugation(7, 8, update, USER_ID).form == "hablé"
    service.delete_conjugation(7, 8, USER_ID)
    assert repository.conjugation is None
    with pytest.raises(HTTPException, match="Vocabulary not found"):
        service.list_conjugations(404, USER_ID)
    with pytest.raises(HTTPException, match="Conjugation not found"):
        service.update_conjugation(7, 404, update, USER_ID)


def test_vocabulary_service_update_and_delete() -> None:
    """Replace and delete vocabulary while validating all referenced resources."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    payload = schemas.VocabularyUpdate(
        text="perro",
        language_id=1,
        category_ids=[3],
        translations=[{"language_id": 2, "text": "dog"}],
    )
    assert service.update_vocabulary(7, payload, USER_ID).text == "perro"
    service.delete_vocabulary(7, USER_ID)
    assert repository.vocabulary is None

    repository.vocabulary = SimpleNamespace(id=7)
    repository.languages.pop(1)
    with pytest.raises(HTTPException, match="Source language"):
        service.update_vocabulary(7, payload, USER_ID)
    repository.languages[1] = repository.es
    payload.chapter_id = 99
    with pytest.raises(HTTPException, match="Chapter"):
        service.update_vocabulary(7, payload, USER_ID)
    payload.chapter_id = 5
    payload.category_ids = [99]
    with pytest.raises(HTTPException, match="categories"):
        service.update_vocabulary(7, payload, USER_ID)
    payload.category_ids = [3]
    payload.translations[0].language_id = 99
    with pytest.raises(HTTPException, match="Translation language"):
        service.update_vocabulary(7, payload, USER_ID)


def test_vocabulary_service_update_conflict() -> None:
    """Translate update uniqueness failures into an HTTP conflict."""
    repository = FakeRepository()
    repository.update_vocabulary = MagicMock(
        side_effect=IntegrityError("duplicate", {}, Exception())
    )
    payload = schemas.VocabularyUpdate(
        text="perro",
        language_id=1,
        translations=[{"language_id": 2, "text": "dog"}],
    )
    with pytest.raises(HTTPException) as error:
        SpanglishService(repository).update_vocabulary(7, payload, USER_ID)
    assert error.value.status_code == 409
    repository.db.rollback.assert_called_once()


@pytest.mark.parametrize("method_name", ["create_conjugation", "update_conjugation"])
def test_conjugation_service_reports_duplicates(method_name) -> None:
    """Translate database uniqueness failures into HTTP conflicts."""
    repository = FakeRepository()
    setattr(
        repository,
        method_name,
        MagicMock(side_effect=IntegrityError("duplicate", {}, Exception())),
    )
    service = SpanglishService(repository)
    payload = schemas.ConjugationUpdate(
        tense="present", mood="indicative", pronoun="yo", form="hablo"
    )
    with pytest.raises(HTTPException) as error:
        if method_name == "create_conjugation":
            service.create_conjugation(
                7, schemas.ConjugationCreate(pronoun="yo", form="hablo"), USER_ID
            )
        else:
            service.update_conjugation(7, 8, payload, USER_ID)
    assert error.value.status_code == 409
    repository.db.rollback.assert_called_once()


def test_generate_quiz_validation_warnings_and_question_types() -> None:
    """Validate language choices and generate a complete mixed quiz."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    payload = schemas.QuizCreateRequest(
        source_language_id=1,
        target_language_id=2,
        question_count=3,
        category_ids=[3],
        chapter_ids=[5],
        question_types=[QuizQuestionType.TRANSLATION, QuizQuestionType.CONJUGATION],
    )
    with pytest.raises(HTTPException, match="No vocabulary"):
        service.generate_quiz(payload, USER_ID)
    repository.rows = [vocabulary_row()]
    response = service.generate_quiz(payload, USER_ID)
    assert response.actual_question_count == 2
    assert response.warnings
    assert {question.type for question in response.questions} == {
        QuizQuestionType.TRANSLATION,
        QuizQuestionType.CONJUGATION,
    }

    repository.languages.pop(1)
    with pytest.raises(HTTPException, match="Source language"):
        service.generate_quiz(payload, USER_ID)
    repository.languages[1] = repository.es
    repository.languages.pop(2)
    with pytest.raises(HTTPException, match="Target language"):
        service.generate_quiz(payload, USER_ID)
    repository.languages[2] = repository.en
    payload.chapter_ids = [99]
    with pytest.raises(HTTPException, match="chapters"):
        service.generate_quiz(payload, USER_ID)


def make_generated_quiz(repository: FakeRepository):
    """Generate a single-question quiz for result tests."""
    repository.rows = [vocabulary_row(conjugations=False)]
    return SpanglishService(repository).generate_quiz(
        schemas.QuizCreateRequest(source_language_id=1, target_language_id=2), USER_ID
    )


def test_submit_result_success_and_all_validation_errors() -> None:
    """Score results and reject missing, duplicate, unknown, or repeated submissions."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    quiz = make_generated_quiz(repository)
    payload = schemas.QuizResultSubmit(
        attempts=[
            {
                "question_id": "translation-7",
                "answer": "to speak",
                "response_time_ms": 12,
            }
        ]
    )
    result = service.submit_result(quiz.quiz_id, payload, USER_ID)
    assert result.score.percentage == 100
    assert result.advice["generated_by_ai"] is False
    assert repository.quiz.attempts[0].answer == {"value": "to speak"}
    history = service.list_quiz_results(USER_ID, 5)
    assert history[0].quiz_id == quiz.quiz_id
    assert history[0].percentage == 100
    with pytest.raises(HTTPException) as repeated:
        service.submit_result(9, payload, USER_ID)
    assert repeated.value.status_code == 409

    repository.quiz.completed_at = None
    duplicate = schemas.QuizResultSubmit(
        attempts=[payload.attempts[0], payload.attempts[0]]
    )
    with pytest.raises(HTTPException, match="more than once"):
        service.submit_result(9, duplicate, USER_ID)
    unknown = schemas.QuizResultSubmit(attempts=[{"question_id": "bad", "answer": "x"}])
    with pytest.raises(HTTPException, match="Unknown"):
        service.submit_result(9, unknown, USER_ID)
    with pytest.raises(HTTPException, match="Missing"):
        service.submit_result(9, schemas.QuizResultSubmit(attempts=[]), USER_ID)
    with pytest.raises(HTTPException, match="Quiz not found"):
        service.submit_result(404, payload, USER_ID)


@pytest.mark.parametrize(
    ("percentage", "phrase"),
    [(90, "Strong"), (60, "Good"), (20, "Review")],
)
def test_advice_levels(percentage, phrase) -> None:
    """Provide useful fallback advice across score bands."""
    assert phrase in SpanglishService._build_advice(1, 2, percentage)["summary"]


def test_evaluate_invalid_translation_and_conjugation_shapes() -> None:
    """Reject wrong transport shapes and empty conjugation definitions."""
    translation = {"type": "translation", "accepted_answers": ["dog"]}
    assert SpanglishService._evaluate(translation, {"value": "dog"}) == (False, 0.0)
    conjugation = {"type": "conjugation", "accepted_answers": {"yo": ["hablo"]}}
    assert SpanglishService._evaluate(conjugation, "hablo") == (False, 0.0)
    assert SpanglishService._evaluate(
        {"type": "conjugation", "accepted_answers": {}}, {}
    ) == (False, 0.0)


def test_repository_crud_and_query_wrappers() -> None:
    """Exercise repository transaction and result adapter behavior with a fake session."""
    db = MagicMock()
    db.scalars.return_value = FakeScalars([SimpleNamespace(id=1, name="A")])
    db.scalar.return_value = 4
    db.execute.return_value = [(3, 2)]
    db.get.side_effect = lambda model, item_id: SimpleNamespace(id=item_id)
    repository = SpanglishRepository(db)

    assert repository.list_languages(USER_ID)[0].name == "A"
    assert repository.list_categories(USER_ID)[0].name == "A"
    assert repository.list_chapters(USER_ID)[0].name == "A"
    assert repository.get_language(1, USER_ID).id == 1
    assert repository.get_chapter(5, USER_ID).id == 1
    assert repository.get_chapters([], USER_ID) == []
    assert repository.get_chapters([5], USER_ID)[0].id == 1
    assert repository.get_categories([], USER_ID) == []
    assert repository.get_categories([3], USER_ID)[0].id == 1
    assert repository.get_vocabulary(1, USER_ID).id == 1
    items, total = repository.list_vocabulary(
        page=1,
        user_id=USER_ID,
        page_size=10,
        language_id=1,
        category_id=3,
        chapter_id=5,
        search="dog",
        randomize=True,
    )
    assert items and total == 4
    assert repository.count_vocabulary_by_category(USER_ID) == {3: 2}
    assert repository.select_quiz_vocabulary(
        source_language_id=1,
        user_id=USER_ID,
        target_language_id=2,
        category_ids=[3],
        chapter_ids=[5],
        limit=10,
        selection_mode=QuizSelectionMode.SEQUENTIAL,
    )
    assert repository.list_quiz_results(USER_ID, 5)

    for creator, arguments in (
        (repository.create_language, (" Spanish ", " ES ", USER_ID)),
        (repository.create_category, (" Animals ", USER_ID)),
        (repository.create_chapter, (" Chapter 1 ", USER_ID)),
    ):
        created = creator(*arguments)
        assert created is not None
    assert db.commit.call_count == 3


def test_repository_aggregate_and_result_persistence() -> None:
    """Create vocabulary, quiz snapshots, and result attempts through repository methods."""
    db = MagicMock()
    repository = SpanglishRepository(db)
    repository.get_vocabulary = MagicMock(return_value="loaded")
    db.add.side_effect = lambda value: setattr(value, "id", 5)
    created = repository.create_vocabulary(
        text=" perro ",
        user_id=USER_ID,
        language_id=1,
        chapter_id=None,
        song_id=None,
        categories=[],
        translations=[{"language_id": 2, "text": " dog "}],
        conjugations=[],
    )
    assert created == "loaded"
    assert db.add.call_args_list[0].args[0].user_id == USER_ID
    quiz = repository.create_quiz(
        source_language_id=1,
        target_language_id=2,
        selection_mode="random",
        requested_question_count=1,
        actual_question_count=1,
        configuration={},
        questions=[],
    )
    assert quiz.id == 5
    repository.save_result(
        quiz,
        [
            models.QuizAttempt(
                vocabulary_id=1,
                question_id="q1",
                answer={"value": "dog"},
                expected_answers=["dog"],
                answered_correctly=True,
                score=1.0,
            )
        ],
    )
    assert len(quiz.attempts) == 1


def test_repository_artist_and_song_operations() -> None:
    """Persist user-owned artists and songs and retrieve selectable rows."""
    db = MagicMock()
    db.add.side_effect = lambda value: setattr(value, "id", 12)
    db.scalars.return_value = FakeScalars(
        [SimpleNamespace(id=12, name="Singer", title="Song", user_id=USER_ID)]
    )
    repository = SpanglishRepository(db)
    assert repository.list_artists(USER_ID)[0].name == "Singer"
    artist = repository.create_artist(" Singer ", USER_ID)
    assert artist.user_id == USER_ID
    assert repository.get_artist(12, USER_ID).id == 12
    assert repository.list_songs(USER_ID)[0].title == "Song"
    assert repository.list_songs(USER_ID, artist_id=12)[0].title == "Song"
    song = repository.create_song(" Song ", artist.id, USER_ID)
    assert song.id == 12
    assert repository.get_song(12, USER_ID).id == 12
    assert db.commit.call_count == 2


def test_reference_options_are_private_to_authenticated_user() -> None:
    """Bootstrap templates privately and never list ownerless or foreign rows."""
    db = MagicMock()
    db.scalars.return_value = FakeScalars([])
    repository = SpanglishRepository(db)
    repository.ensure_user_references(USER_ID)
    assert db.execute.call_count == 3
    assert all(
        call.args[1] == {"user_id": USER_ID} for call in db.execute.call_args_list
    )
    for list_method in (
        repository.list_languages,
        repository.list_categories,
        repository.list_chapters,
    ):
        list_method(USER_ID)
        statement = str(db.scalars.call_args.args[0])
        assert "user_id =" in statement
        assert "IS NULL" not in statement


def test_vocabulary_and_quiz_queries_filter_by_authenticated_user() -> None:
    """Guard every learner-data read against cross-account disclosure."""
    db = MagicMock()
    db.scalars.return_value = FakeScalars([])
    db.scalar.return_value = 0
    repository = SpanglishRepository(db)
    repository.list_vocabulary(
        user_id=USER_ID,
        page=1,
        page_size=10,
        language_id=None,
        category_id=None,
        chapter_id=None,
        search=None,
    )
    assert "vocabulary.user_id =" in str(db.scalars.call_args.args[0])
    repository.select_quiz_vocabulary(
        user_id=USER_ID,
        source_language_id=1,
        target_language_id=2,
        category_ids=[],
        chapter_ids=[],
        limit=10,
        selection_mode=QuizSelectionMode.SEQUENTIAL,
    )
    assert "vocabulary.user_id =" in str(db.scalars.call_args.args[0])
    repository.get_quiz(9, USER_ID)
    assert "quiz_sessions.user_id =" in str(db.scalars.call_args.args[0])
    repository.list_quiz_results(USER_ID, 5)
    assert "quiz_sessions.user_id =" in str(db.scalars.call_args.args[0])


def test_repository_updates_and_deletes_vocabulary_aggregate() -> None:
    """Replace nested vocabulary rows and delegate aggregate deletion to SQLAlchemy."""
    db = MagicMock()
    repository = SpanglishRepository(db)
    vocabulary = models.Vocabulary(id=7, text="perro", language_id=1)
    repository.get_vocabulary = MagicMock(return_value=vocabulary)
    updated = repository.update_vocabulary(
        vocabulary,
        text=" hablar ",
        language_id=1,
        chapter_id=None,
        song_id=None,
        categories=[],
        translations=[{"language_id": 2, "text": " speak "}],
        conjugations=[
            {
                "tense": "present",
                "mood": "indicative",
                "pronoun": "yo",
                "form": "hablo",
            }
        ],
    )
    assert updated.text == "hablar"
    assert updated.translations[0].translation == "speak"
    repository.delete_vocabulary(vocabulary)
    db.delete.assert_called_once_with(vocabulary)


def test_repository_conjugation_crud() -> None:
    """Exercise all nested conjugation persistence operations."""
    db = MagicMock()
    conjugation = models.VerbConjugation(
        id=8,
        vocabulary_id=7,
        tense="present",
        mood="indicative",
        pronoun="yo",
        form="hablo",
    )
    db.scalars.return_value = FakeScalars([conjugation])
    repository = SpanglishRepository(db)
    assert repository.list_conjugations(7, USER_ID) == [conjugation]
    assert repository.get_conjugation(7, 8, USER_ID) is conjugation
    created = repository.create_conjugation(
        7, USER_ID, tense="present", mood="indicative", pronoun="tú", form="hablas"
    )
    assert created.form == "hablas"
    updated = repository.update_conjugation(created, form="hablaste")
    assert updated.form == "hablaste"
    repository.delete_conjugation(updated)
    db.delete.assert_called_once_with(updated)


def test_route_functions_delegate_without_http_server() -> None:
    """Cover thin FastAPI wrappers independently from database integration."""
    repository = MagicMock()
    service = MagicMock()
    repository.list_languages.return_value = []
    repository.list_categories.return_value = []
    repository.list_chapters.return_value = []
    repository.list_vocabulary.return_value = ([], 0)
    repository.get_vocabulary.return_value = SimpleNamespace(id=1)
    assert routers.get_repository(repository) is not None
    assert routers.get_service(repository).repository is repository
    user = SimpleNamespace(id=USER_ID)
    routers.get_quiz_options(service, user)
    routers.list_languages(repository, user)
    routers.create_language(
        schemas.LanguageCreate(name="Spanish", code="es"), repository, user
    )
    routers.list_categories(repository, user)
    routers.create_category(schemas.ReferenceCreate(name="Animals"), repository, user)
    routers.list_chapters(repository, user)
    routers.create_chapter(schemas.ReferenceCreate(name="Chapter 1"), repository, user)
    routers.list_artists(repository, user)
    routers.create_artist(schemas.ReferenceCreate(name="Singer"), repository, user)
    repository.create_artist.side_effect = IntegrityError("duplicate", {}, Exception())
    with pytest.raises(HTTPException, match="Artist already exists"):
        routers.create_artist(schemas.ReferenceCreate(name="Singer"), repository, user)
    repository.create_artist.side_effect = None
    routers.list_songs(None, repository, user)
    repository.get_artist.return_value = SimpleNamespace(id=12)
    routers.create_song(
        schemas.SongCreate(title="Song", artist_id=12), repository, user
    )
    repository.create_song.side_effect = IntegrityError("duplicate", {}, Exception())
    with pytest.raises(HTTPException, match="Song already exists"):
        routers.create_song(
            schemas.SongCreate(title="Song", artist_id=12), repository, user
        )
    repository.create_song.side_effect = None
    repository.get_artist.return_value = None
    with pytest.raises(HTTPException, match="Artist not found"):
        routers.create_song(
            schemas.SongCreate(title="Song", artist_id=12), repository, user
        )
    routers.create_vocabulary(MagicMock(), service, user)
    response = routers.list_vocabulary(
        page=1,
        page_size=20,
        language_id=None,
        category_id=None,
        chapter_id=None,
        search=None,
        randomize=False,
        repository=repository,
        current_user=user,
    )
    assert response.total == 0
    assert routers.get_vocabulary(1, repository, user).id == 1
    vocabulary_update = schemas.VocabularyUpdate(
        text="perro",
        language_id=1,
        translations=[{"language_id": 2, "text": "dog"}],
    )
    routers.update_vocabulary(1, vocabulary_update, service, user)
    assert routers.delete_vocabulary(1, service, user).status_code == 204
    service.list_conjugations.return_value = []
    assert routers.list_conjugations(1, service, user) == []
    conjugation_create = schemas.ConjugationCreate(pronoun="yo", form="hablo")
    conjugation_update = schemas.ConjugationUpdate(
        tense="present", mood="indicative", pronoun="yo", form="hablé"
    )
    routers.create_conjugation(1, conjugation_create, service, user)
    routers.update_conjugation(1, 2, conjugation_update, service, user)
    assert routers.delete_conjugation(1, 2, service, user).status_code == 204
    routers.create_quiz(MagicMock(), service, user)
    routers.list_quiz_results(5, service, user)
    routers.submit_quiz_result(1, MagicMock(), service, user)
    repository.get_vocabulary.return_value = None
    with pytest.raises(HTTPException):
        routers.get_vocabulary(404, repository, user)
