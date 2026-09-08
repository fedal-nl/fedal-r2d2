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
    word = SimpleNamespace(id=4, name="Word")
    chapter = SimpleNamespace(id=5, name="Chapter 1")
    return es, en, category, word, chapter


class FakeRepository:
    """Provide configurable persistence behavior to service unit tests."""

    def __init__(self):
        self.es, self.en, self.category, self.word, self.chapter = reference_data()
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

    def count_vocabulary_by_category(self):
        return {3: 2}

    def list_categories(self):
        return self.categories

    def list_languages(self):
        return list(self.languages.values())

    def list_vocabulary_types(self):
        return [self.word]

    def list_chapters(self):
        return [self.chapter]

    def get_language(self, value):
        return self.languages.get(value)

    def get_vocabulary_type(self, value):
        return self.word if value == 4 else None

    def get_chapter(self, value):
        return self.chapter if value == 5 else None

    def get_chapters(self, values):
        return [self.chapter] if values == [5] else []

    def get_categories(self, values):
        return self.categories if values == [3] else []

    def create_vocabulary(self, **values):
        return values

    def update_vocabulary(self, vocabulary, **values):
        for field, value in values.items():
            setattr(vocabulary, field, value)
        return vocabulary

    def delete_vocabulary(self, vocabulary):
        self.vocabulary = None

    def get_vocabulary(self, value):
        return self.vocabulary if value == 7 else None

    def list_conjugations(self, value):
        return [self.conjugation] if value == 7 else []

    def get_conjugation(self, vocabulary_id, conjugation_id):
        if vocabulary_id == 7 and conjugation_id == 8:
            return self.conjugation
        return None

    def create_conjugation(self, vocabulary_id, **values):
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
    options = service.get_quiz_options()
    assert options.categories[0].available_questions == 2
    assert options.chapters[0].name == "Chapter 1"
    payload = schemas.VocabularyCreate(
        text="perro",
        language_id=1,
        vocabulary_type_id=4,
        chapter_id=5,
        category_ids=[3],
        translations=[{"language_id": 2, "text": "dog"}],
    )
    assert service.create_vocabulary(payload)["text"] == "perro"

    repository.languages.pop(1)
    with pytest.raises(HTTPException, match="Source language"):
        service.create_vocabulary(payload)
    repository.languages[1] = repository.es
    payload.vocabulary_type_id = 99
    with pytest.raises(HTTPException, match="Vocabulary type"):
        service.create_vocabulary(payload)
    payload.vocabulary_type_id = 4
    payload.chapter_id = 99
    with pytest.raises(HTTPException, match="Chapter"):
        service.create_vocabulary(payload)
    payload.chapter_id = 5
    payload.category_ids = [99]
    with pytest.raises(HTTPException, match="categories"):
        service.create_vocabulary(payload)
    payload.category_ids = [3]
    payload.translations[0].language_id = 99
    with pytest.raises(HTTPException, match="Translation language"):
        service.create_vocabulary(payload)


def test_service_translates_integrity_error_to_conflict() -> None:
    """Return a useful conflict when vocabulary uniqueness is violated."""
    repository = FakeRepository()
    repository.create_vocabulary = MagicMock(
        side_effect=IntegrityError("x", {}, Exception())
    )
    payload = schemas.VocabularyCreate(
        text="perro",
        language_id=1,
        vocabulary_type_id=4,
        chapter_id=5,
        translations=[{"language_id": 2, "text": "dog"}],
    )
    with pytest.raises(HTTPException) as error:
        SpanglishService(repository).create_vocabulary(payload)
    assert error.value.status_code == 409
    repository.db.rollback.assert_called_once()


def test_conjugation_service_crud_and_not_found() -> None:
    """Create, list, replace, and delete forms while enforcing ownership."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    create = schemas.ConjugationCreate(pronoun="tú", form="hablas")
    update = schemas.ConjugationUpdate(
        tense="present", mood="indicative", pronoun="yo", form="hablé"
    )
    assert service.list_conjugations(7)[0].form == "hablo"
    assert service.create_conjugation(7, create).form == "hablas"
    assert service.update_conjugation(7, 8, update).form == "hablé"
    service.delete_conjugation(7, 8)
    assert repository.conjugation is None
    with pytest.raises(HTTPException, match="Vocabulary not found"):
        service.list_conjugations(404)
    with pytest.raises(HTTPException, match="Conjugation not found"):
        service.update_conjugation(7, 404, update)


def test_vocabulary_service_update_and_delete() -> None:
    """Replace and delete vocabulary while validating all referenced resources."""
    repository = FakeRepository()
    service = SpanglishService(repository)
    payload = schemas.VocabularyUpdate(
        text="perro",
        language_id=1,
        vocabulary_type_id=4,
        category_ids=[3],
        translations=[{"language_id": 2, "text": "dog"}],
    )
    assert service.update_vocabulary(7, payload).text == "perro"
    service.delete_vocabulary(7)
    assert repository.vocabulary is None

    repository.vocabulary = SimpleNamespace(id=7)
    repository.languages.pop(1)
    with pytest.raises(HTTPException, match="Source language"):
        service.update_vocabulary(7, payload)
    repository.languages[1] = repository.es
    payload.vocabulary_type_id = 99
    with pytest.raises(HTTPException, match="Vocabulary type"):
        service.update_vocabulary(7, payload)
    payload.vocabulary_type_id = 4
    payload.chapter_id = 99
    with pytest.raises(HTTPException, match="Chapter"):
        service.update_vocabulary(7, payload)
    payload.chapter_id = 5
    payload.category_ids = [99]
    with pytest.raises(HTTPException, match="categories"):
        service.update_vocabulary(7, payload)
    payload.category_ids = [3]
    payload.translations[0].language_id = 99
    with pytest.raises(HTTPException, match="Translation language"):
        service.update_vocabulary(7, payload)


def test_vocabulary_service_update_conflict() -> None:
    """Translate update uniqueness failures into an HTTP conflict."""
    repository = FakeRepository()
    repository.update_vocabulary = MagicMock(
        side_effect=IntegrityError("duplicate", {}, Exception())
    )
    payload = schemas.VocabularyUpdate(
        text="perro",
        language_id=1,
        vocabulary_type_id=4,
        translations=[{"language_id": 2, "text": "dog"}],
    )
    with pytest.raises(HTTPException) as error:
        SpanglishService(repository).update_vocabulary(7, payload)
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
                7, schemas.ConjugationCreate(pronoun="yo", form="hablo")
            )
        else:
            service.update_conjugation(7, 8, payload)
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
        vocabulary_type_ids=[4],
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

    assert repository.list_languages()[0].name == "A"
    assert repository.list_categories()[0].name == "A"
    assert repository.list_vocabulary_types()[0].name == "A"
    assert repository.list_chapters()[0].name == "A"
    assert repository.get_language(1).id == 1
    assert repository.get_vocabulary_type(2).id == 2
    assert repository.get_chapter(5).id == 5
    assert repository.get_chapters([]) == []
    assert repository.get_chapters([5])[0].id == 1
    assert repository.get_categories([]) == []
    assert repository.get_categories([3])[0].id == 1
    assert repository.get_vocabulary(1).id == 1
    items, total = repository.list_vocabulary(
        page=1,
        page_size=10,
        language_id=1,
        category_id=3,
        chapter_id=5,
        search="dog",
        randomize=True,
    )
    assert items and total == 4
    assert repository.count_vocabulary_by_category() == {3: 2}
    assert repository.select_quiz_vocabulary(
        source_language_id=1,
        target_language_id=2,
        category_ids=[3],
        chapter_ids=[5],
        vocabulary_type_ids=[4],
        limit=10,
        selection_mode=QuizSelectionMode.SEQUENTIAL,
    )

    for creator, arguments in (
        (repository.create_language, (" Spanish ", " ES ")),
        (repository.create_category, (" Animals ",)),
        (repository.create_chapter, (" Chapter 1 ",)),
        (repository.create_vocabulary_type, (" Word ",)),
    ):
        created = creator(*arguments)
        assert created is not None
    assert db.commit.call_count == 4


def test_repository_aggregate_and_result_persistence() -> None:
    """Create vocabulary, quiz snapshots, and result attempts through repository methods."""
    db = MagicMock()
    repository = SpanglishRepository(db)
    repository.get_vocabulary = MagicMock(return_value="loaded")
    db.add.side_effect = lambda value: setattr(value, "id", 5)
    created = repository.create_vocabulary(
        text=" perro ",
        language_id=1,
        vocabulary_type_id=4,
        chapter_id=None,
        categories=[],
        translations=[{"language_id": 2, "text": " dog "}],
        conjugations=[],
    )
    assert created == "loaded"
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


def test_repository_updates_and_deletes_vocabulary_aggregate() -> None:
    """Replace nested vocabulary rows and delegate aggregate deletion to SQLAlchemy."""
    db = MagicMock()
    repository = SpanglishRepository(db)
    vocabulary = models.Vocabulary(
        id=7, text="perro", language_id=1, vocabulary_type_id=4
    )
    repository.get_vocabulary = MagicMock(return_value=vocabulary)
    updated = repository.update_vocabulary(
        vocabulary,
        text=" hablar ",
        language_id=1,
        vocabulary_type_id=4,
        chapter_id=None,
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
    assert repository.list_conjugations(7) == [conjugation]
    assert repository.get_conjugation(7, 8) is conjugation
    created = repository.create_conjugation(
        7, tense="present", mood="indicative", pronoun="tú", form="hablas"
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
    repository.list_vocabulary_types.return_value = []
    repository.list_vocabulary.return_value = ([], 0)
    repository.get_vocabulary.return_value = SimpleNamespace(id=1)
    assert routers.get_repository(repository) is not None
    assert routers.get_service(repository).repository is repository
    routers.get_quiz_options(service)
    routers.list_languages(repository)
    routers.create_language(
        schemas.LanguageCreate(name="Spanish", code="es"), repository
    )
    routers.list_categories(repository)
    routers.create_category(schemas.ReferenceCreate(name="Animals"), repository)
    routers.list_chapters(repository)
    routers.create_chapter(schemas.ReferenceCreate(name="Chapter 1"), repository)
    routers.list_vocabulary_types(repository)
    routers.create_vocabulary_type(schemas.ReferenceCreate(name="Word"), repository)
    routers.create_vocabulary(MagicMock(), service)
    response = routers.list_vocabulary(
        page=1,
        page_size=20,
        language_id=None,
        category_id=None,
        chapter_id=None,
        search=None,
        randomize=False,
        repository=repository,
    )
    assert response.total == 0
    assert routers.get_vocabulary(1, repository).id == 1
    vocabulary_update = schemas.VocabularyUpdate(
        text="perro",
        language_id=1,
        vocabulary_type_id=1,
        translations=[{"language_id": 2, "text": "dog"}],
    )
    routers.update_vocabulary(1, vocabulary_update, service)
    assert routers.delete_vocabulary(1, service).status_code == 204
    service.list_conjugations.return_value = []
    assert routers.list_conjugations(1, service) == []
    conjugation_create = schemas.ConjugationCreate(pronoun="yo", form="hablo")
    conjugation_update = schemas.ConjugationUpdate(
        tense="present", mood="indicative", pronoun="yo", form="hablé"
    )
    routers.create_conjugation(1, conjugation_create, service)
    routers.update_conjugation(1, 2, conjugation_update, service)
    assert routers.delete_conjugation(1, 2, service).status_code == 204
    user = SimpleNamespace(id=USER_ID)
    routers.create_quiz(MagicMock(), service, user)
    routers.submit_quiz_result(1, MagicMock(), service, user)
    repository.get_vocabulary.return_value = None
    with pytest.raises(HTTPException):
        routers.get_vocabulary(404, repository)
