"""Focused tests for deterministic Spanglish quiz behavior."""

from types import SimpleNamespace

from src.apps.spanglish.schemas import QuizCreateRequest
from src.apps.spanglish.services import (
    SpanglishService,
    answer_matches,
    normalize_answer,
)
from src.enums import QuizQuestionType, QuizSelectionMode


def test_answer_normalization_is_exact_but_user_friendly() -> None:
    """Normalize harmless formatting without accepting substring answers."""
    assert normalize_answer("  DOG. ") == "dog"
    assert answer_matches("Dog!", ["dog", "hound"])
    assert not answer_matches("do", ["dog"])
    assert not answer_matches("", ["dog"])


def test_build_questions_supports_both_translation_directions() -> None:
    """Use translations as prompts when the selected direction is reversed."""
    vocabulary = SimpleNamespace(
        id=7,
        text="perro",
        language_id=1,
        categories=[SimpleNamespace(id=3)],
        translations=[SimpleNamespace(language_id=2, translation="dog")],
        verb_conjugations=[],
    )
    forward = QuizCreateRequest(source_language_id=1, target_language_id=2)
    reverse = QuizCreateRequest(source_language_id=2, target_language_id=1)

    forward_question = SpanglishService._build_questions([vocabulary], forward)[0]
    reverse_question = SpanglishService._build_questions([vocabulary], reverse)[0]

    assert (forward_question.prompt, forward_question.accepted_answers) == (
        "perro",
        ["dog"],
    )
    assert (reverse_question.prompt, reverse_question.accepted_answers) == (
        "dog",
        ["perro"],
    )


def test_conjugation_evaluation_returns_partial_score() -> None:
    """Award granular credit while requiring every form for full correctness."""
    question = {
        "type": QuizQuestionType.CONJUGATION.value,
        "accepted_answers": {"yo": ["hablo"], "tú": ["hablas"]},
    }
    correct, score = SpanglishService._evaluate(
        question, {"yo": "hablo", "tú": "incorrect"}
    )
    assert not correct
    assert score == 0.5


def test_quiz_request_serializes_selection_mode() -> None:
    """Keep the quiz builder contract stable for every client interface."""
    request = QuizCreateRequest(
        source_language_id=1,
        target_language_id=2,
        selection_mode=QuizSelectionMode.SEQUENTIAL,
    )
    assert request.model_dump(mode="json")["selection_mode"] == "sequential"
