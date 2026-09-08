"""Business rules for vocabulary, batch quizzes, scoring, and advice."""

import re
import unicodedata
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from src.apps.spanglish import models, schemas
from src.apps.spanglish.repositories import SpanglishRepository
from src.enums import QuizQuestionType, QuizSelectionMode


def normalize_answer(value: str) -> str:
    """Normalize case, Unicode, whitespace, and terminal punctuation for comparison."""
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.rstrip(".?!")


def answer_matches(answer: str, accepted_answers: list[str]) -> bool:
    """Compare an answer exactly against individually normalized alternatives."""
    normalized_answer = normalize_answer(answer)
    return bool(normalized_answer) and normalized_answer in {
        normalize_answer(candidate) for candidate in accepted_answers
    }


class SpanglishService:
    """Coordinate validation, persistence, quiz generation, and scoring."""

    def __init__(self, repository: SpanglishRepository):
        """Receive a repository so business rules stay independently testable."""
        self.repository = repository

    def get_quiz_options(self) -> schemas.QuizOptionsResponse:
        """Build the metadata used by CLI menus and graphical quiz builders."""
        counts = self.repository.count_vocabulary_by_category()
        categories = [
            schemas.CategoryOption(
                id=item.id, name=item.name, available_questions=counts.get(item.id, 0)
            )
            for item in self.repository.list_categories()
        ]
        return schemas.QuizOptionsResponse(
            languages=self.repository.list_languages(),
            categories=categories,
            chapters=self.repository.list_chapters(),
            vocabulary_types=self.repository.list_vocabulary_types(),
            selection_modes=list(QuizSelectionMode),
            question_types=list(QuizQuestionType),
        )

    def create_vocabulary(self, payload: schemas.VocabularyCreate) -> models.Vocabulary:
        """Validate references and persist a complete vocabulary aggregate."""
        if not self.repository.get_language(payload.language_id):
            raise HTTPException(status_code=404, detail="Source language not found")
        if not self.repository.get_vocabulary_type(payload.vocabulary_type_id):
            raise HTTPException(status_code=404, detail="Vocabulary type not found")
        if payload.chapter_id is not None and not self.repository.get_chapter(
            payload.chapter_id
        ):
            raise HTTPException(status_code=404, detail="Chapter not found")
        categories = self.repository.get_categories(payload.category_ids)
        if len(categories) != len(set(payload.category_ids)):
            raise HTTPException(
                status_code=404, detail="One or more categories were not found"
            )
        for translation in payload.translations:
            if not self.repository.get_language(translation.language_id):
                raise HTTPException(
                    status_code=404,
                    detail=f"Translation language {translation.language_id} not found",
                )
        try:
            return self.repository.create_vocabulary(
                text=payload.text,
                language_id=payload.language_id,
                vocabulary_type_id=payload.vocabulary_type_id,
                chapter_id=payload.chapter_id,
                categories=categories,
                translations=[item.model_dump() for item in payload.translations],
                conjugations=[item.model_dump() for item in payload.conjugations],
            )
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=409, detail="Vocabulary or translation already exists"
            ) from exc

    def update_vocabulary(
        self, vocabulary_id: int, payload: schemas.VocabularyUpdate
    ) -> models.Vocabulary:
        """Validate and replace an existing vocabulary aggregate."""
        vocabulary = self._require_vocabulary(vocabulary_id)
        if not self.repository.get_language(payload.language_id):
            raise HTTPException(status_code=404, detail="Source language not found")
        if not self.repository.get_vocabulary_type(payload.vocabulary_type_id):
            raise HTTPException(status_code=404, detail="Vocabulary type not found")
        if payload.chapter_id is not None and not self.repository.get_chapter(
            payload.chapter_id
        ):
            raise HTTPException(status_code=404, detail="Chapter not found")
        categories = self.repository.get_categories(payload.category_ids)
        if len(categories) != len(set(payload.category_ids)):
            raise HTTPException(
                status_code=404, detail="One or more categories were not found"
            )
        for translation in payload.translations:
            if not self.repository.get_language(translation.language_id):
                raise HTTPException(
                    status_code=404,
                    detail=f"Translation language {translation.language_id} not found",
                )
        try:
            return self.repository.update_vocabulary(
                vocabulary,
                text=payload.text,
                language_id=payload.language_id,
                vocabulary_type_id=payload.vocabulary_type_id,
                chapter_id=payload.chapter_id,
                categories=categories,
                translations=[item.model_dump() for item in payload.translations],
                conjugations=[item.model_dump() for item in payload.conjugations],
            )
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=409, detail="Vocabulary or translation already exists"
            ) from exc

    def delete_vocabulary(self, vocabulary_id: int) -> None:
        """Delete an existing vocabulary aggregate."""
        vocabulary = self._require_vocabulary(vocabulary_id)
        self.repository.delete_vocabulary(vocabulary)

    def list_conjugations(self, vocabulary_id: int) -> list[models.VerbConjugation]:
        """Return conjugations after confirming the vocabulary item exists."""
        self._require_vocabulary(vocabulary_id)
        return self.repository.list_conjugations(vocabulary_id)

    def create_conjugation(
        self, vocabulary_id: int, payload: schemas.ConjugationCreate
    ) -> models.VerbConjugation:
        """Add a conjugation to existing vocabulary and report duplicates cleanly."""
        self._require_vocabulary(vocabulary_id)
        try:
            return self.repository.create_conjugation(
                vocabulary_id, **payload.model_dump()
            )
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="This tense, mood, and pronoun already exist for the vocabulary item",
            ) from exc

    def update_conjugation(
        self,
        vocabulary_id: int,
        conjugation_id: int,
        payload: schemas.ConjugationUpdate,
    ) -> models.VerbConjugation:
        """Replace an existing conjugation that belongs to the vocabulary item."""
        conjugation = self._require_conjugation(vocabulary_id, conjugation_id)
        try:
            return self.repository.update_conjugation(
                conjugation, **payload.model_dump()
            )
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="This tense, mood, and pronoun already exist for the vocabulary item",
            ) from exc

    def delete_conjugation(self, vocabulary_id: int, conjugation_id: int) -> None:
        """Delete an existing conjugation owned by the vocabulary item."""
        conjugation = self._require_conjugation(vocabulary_id, conjugation_id)
        self.repository.delete_conjugation(conjugation)

    def generate_quiz(
        self, payload: schemas.QuizCreateRequest, user_id
    ) -> schemas.QuizResponse:
        """Generate all requested questions and persist their immutable snapshot."""
        if not self.repository.get_language(payload.source_language_id):
            raise HTTPException(status_code=404, detail="Source language not found")
        if not self.repository.get_language(payload.target_language_id):
            raise HTTPException(status_code=404, detail="Target language not found")
        chapters = self.repository.get_chapters(payload.chapter_ids)
        if len(chapters) != len(set(payload.chapter_ids)):
            raise HTTPException(
                status_code=404, detail="One or more chapters were not found"
            )
        rows = self.repository.select_quiz_vocabulary(
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
            category_ids=payload.category_ids,
            chapter_ids=payload.chapter_ids,
            vocabulary_type_ids=payload.vocabulary_type_ids,
            limit=payload.question_count,
            selection_mode=payload.selection_mode,
        )
        questions = self._build_questions(rows, payload)[: payload.question_count]
        if not questions:
            raise HTTPException(
                status_code=404,
                detail="No vocabulary matches the selected quiz options",
            )
        configuration = payload.model_dump(mode="json")
        quiz = self.repository.create_quiz(
            user_id=user_id,
            source_language_id=payload.source_language_id,
            target_language_id=payload.target_language_id,
            selection_mode=payload.selection_mode.value,
            requested_question_count=payload.question_count,
            actual_question_count=len(questions),
            configuration=configuration,
            questions=[item.model_dump(mode="json") for item in questions],
            client_type=payload.client_type,
        )
        warnings = []
        if len(questions) < payload.question_count:
            warnings.append(f"Only {len(questions)} matching questions were available.")
        return schemas.QuizResponse(
            quiz_id=quiz.id,
            generated_at=quiz.created_at,
            requested_question_count=quiz.requested_question_count,
            actual_question_count=quiz.actual_question_count,
            configuration=quiz.configuration,
            warnings=warnings,
            questions=questions,
        )

    def submit_result(
        self, quiz_id: int, payload: schemas.QuizResultSubmit, user_id
    ) -> schemas.QuizResultResponse:
        """Recalculate every answer, persist attempts, and return deterministic advice."""
        quiz = self.repository.get_quiz(quiz_id, user_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        if quiz.completed_at is not None:
            raise HTTPException(
                status_code=409, detail="Quiz results were already submitted"
            )
        questions = {question["id"]: question for question in (quiz.questions or [])}
        submitted_ids = [attempt.question_id for attempt in payload.attempts]
        if len(submitted_ids) != len(set(submitted_ids)):
            raise HTTPException(
                status_code=422, detail="A question was submitted more than once"
            )
        unknown = set(submitted_ids) - set(questions)
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown question IDs: {sorted(unknown)}"
            )
        missing = set(questions) - set(submitted_ids)
        if missing:
            raise HTTPException(
                status_code=422, detail=f"Missing question IDs: {sorted(missing)}"
            )
        evaluations = []
        attempt_models = []
        for submitted in payload.attempts:
            question = questions[submitted.question_id]
            correct, score = self._evaluate(question, submitted.answer)
            feedback = (
                "Correct."
                if correct
                else "Review the accepted answer and try this item again."
            )
            evaluations.append(
                schemas.AttemptEvaluation(
                    question_id=submitted.question_id,
                    correct=correct,
                    score=score,
                    accepted_answers=question["accepted_answers"],
                    feedback=feedback,
                )
            )
            answer_value = (
                submitted.answer
                if isinstance(submitted.answer, dict)
                else {"value": submitted.answer}
            )
            attempt_models.append(
                models.QuizAttempt(
                    vocabulary_id=question["vocabulary_id"],
                    question_id=submitted.question_id,
                    answer=answer_value,
                    expected_answers=question["accepted_answers"],
                    answered_correctly=correct,
                    score=score,
                    response_time_ms=submitted.response_time_ms,
                    feedback=feedback,
                )
            )
        correct_count = sum(item.correct for item in evaluations)
        total = len(questions)
        percentage = (
            round((sum(item.score for item in evaluations) / total) * 100, 2)
            if total
            else 0.0
        )
        advice = self._build_advice(correct_count, total, percentage)
        quiz.completed_at = payload.completed_at or datetime.now(UTC)
        quiz.client_type = payload.client_type or quiz.client_type
        quiz.correct_count = correct_count
        quiz.score_percentage = percentage
        quiz.advice = advice
        self.repository.save_result(quiz, attempt_models)
        return schemas.QuizResultResponse(
            result_id=quiz.id,
            quiz_id=quiz.id,
            score=schemas.ScoreResponse(
                correct=correct_count,
                incorrect=total - correct_count,
                total=total,
                percentage=percentage,
            ),
            attempts=evaluations,
            advice=advice,
        )

    @staticmethod
    def _build_questions(
        rows: list[models.Vocabulary], payload: schemas.QuizCreateRequest
    ) -> list[schemas.QuizQuestion]:
        """Convert selected vocabulary into transport-safe translation and conjugation questions."""
        questions: list[schemas.QuizQuestion] = []
        for vocabulary in rows:
            reverse = vocabulary.language_id == payload.target_language_id
            matching_translations = [
                item.translation
                for item in vocabulary.translations
                if item.language_id
                == (
                    payload.source_language_id
                    if reverse
                    else payload.target_language_id
                )
            ]
            category_ids = [item.id for item in vocabulary.categories]
            if (
                QuizQuestionType.TRANSLATION in payload.question_types
                and matching_translations
            ):
                prompt = matching_translations[0] if reverse else vocabulary.text
                accepted = [vocabulary.text] if reverse else matching_translations
                questions.append(
                    schemas.QuizQuestion(
                        id=f"translation-{vocabulary.id}",
                        vocabulary_id=vocabulary.id,
                        type=QuizQuestionType.TRANSLATION,
                        prompt=prompt,
                        accepted_answers=accepted,
                        category_ids=category_ids,
                    )
                )
            if (
                QuizQuestionType.CONJUGATION in payload.question_types
                and vocabulary.verb_conjugations
            ):
                accepted_forms = {
                    item.pronoun: [item.form] for item in vocabulary.verb_conjugations
                }
                questions.append(
                    schemas.QuizQuestion(
                        id=f"conjugation-{vocabulary.id}",
                        vocabulary_id=vocabulary.id,
                        type=QuizQuestionType.CONJUGATION,
                        prompt=f"Conjugate {vocabulary.text}",
                        accepted_answers=accepted_forms,
                        category_ids=category_ids,
                    )
                )
        return questions

    @staticmethod
    def _evaluate(
        question: dict, submitted_answer: str | dict[str, str]
    ) -> tuple[bool, float]:
        """Evaluate translation or conjugation data without trusting client scoring."""
        accepted = question["accepted_answers"]
        if question["type"] == QuizQuestionType.TRANSLATION.value:
            correct = isinstance(submitted_answer, str) and answer_matches(
                submitted_answer, accepted
            )
            return correct, 1.0 if correct else 0.0
        if not isinstance(submitted_answer, dict) or not isinstance(accepted, dict):
            return False, 0.0
        results = [
            answer_matches(submitted_answer.get(pronoun, ""), answers)
            for pronoun, answers in accepted.items()
        ]
        score = sum(results) / len(results) if results else 0.0
        return bool(results) and all(results), round(score, 2)

    @staticmethod
    def _build_advice(correct: int, total: int, percentage: float) -> dict:
        """Return reliable fallback advice behind an AI-ready response shape."""
        if percentage >= 80:
            summary = "Strong result. Continue with a larger quiz or another category."
        elif percentage >= 50:
            summary = "Good progress. Review the missed answers before trying again."
        else:
            summary = "Review this vocabulary set and retry a shorter quiz."
        return {
            "summary": summary,
            "recommendations": [
                "Review incorrect answers.",
                "Repeat the quiz after practising.",
            ],
            "generated_by_ai": False,
            "correct": correct,
            "total": total,
        }

    def _require_vocabulary(self, vocabulary_id: int) -> models.Vocabulary:
        """Return vocabulary or raise the API's standard not-found response."""
        vocabulary = self.repository.get_vocabulary(vocabulary_id)
        if vocabulary is None:
            raise HTTPException(status_code=404, detail="Vocabulary not found")
        return vocabulary

    def _require_conjugation(
        self, vocabulary_id: int, conjugation_id: int
    ) -> models.VerbConjugation:
        """Return an owned conjugation or raise a non-leaking not-found response."""
        conjugation = self.repository.get_conjugation(vocabulary_id, conjugation_id)
        if conjugation is None:
            raise HTTPException(status_code=404, detail="Conjugation not found")
        return conjugation
