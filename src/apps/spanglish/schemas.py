"""Public request and response contracts for the Spanglish API."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.enums import QuizQuestionType, QuizSelectionMode


class ReferenceCreate(BaseModel):
    """Create a named language-independent reference value."""

    name: str = Field(min_length=1, max_length=100)


class LanguageCreate(ReferenceCreate):
    """Create a language that can participate in translations."""

    code: str = Field(min_length=2, max_length=10)


class ReferenceResponse(BaseModel):
    """Return a reference value used by client selection controls."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class LanguageResponse(ReferenceResponse):
    """Return a language and its stable short code."""

    code: str


class CategoryOption(ReferenceResponse):
    """Return a category with its available translation question count."""

    available_questions: int = 0


class QuizOptionsResponse(BaseModel):
    """Describe all server-supported controls for a quiz builder UI."""

    languages: list[LanguageResponse]
    categories: list[CategoryOption]
    chapters: list[ReferenceResponse]
    vocabulary_types: list[ReferenceResponse]
    selection_modes: list[QuizSelectionMode]
    question_types: list[QuizQuestionType]
    default_question_count: int = 10
    maximum_question_count: int = 100


class TranslationCreate(BaseModel):
    """Add an accepted translation in a specific target language."""

    language_id: int
    text: str = Field(min_length=1, max_length=500)


class TranslationResponse(BaseModel):
    """Return a persisted accepted translation."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    language_id: int
    translation: str


class ConjugationCreate(BaseModel):
    """Add one structured verb form to a vocabulary item."""

    tense: str = Field(default="present", min_length=1, max_length=50)
    mood: str = Field(default="indicative", min_length=1, max_length=50)
    pronoun: str = Field(min_length=1, max_length=50)
    form: str = Field(min_length=1, max_length=100)


class ConjugationResponse(ConjugationCreate):
    """Return a persisted structured verb form."""

    model_config = ConfigDict(from_attributes=True)
    id: int


class ConjugationUpdate(BaseModel):
    """Replace the grammatical identity and form of a conjugation."""

    tense: str = Field(min_length=1, max_length=50)
    mood: str = Field(min_length=1, max_length=50)
    pronoun: str = Field(min_length=1, max_length=50)
    form: str = Field(min_length=1, max_length=100)


class VocabularyCreate(BaseModel):
    """Create vocabulary and all data needed for its first quiz card."""

    text: str = Field(min_length=1, max_length=500)
    language_id: int
    vocabulary_type_id: int
    chapter_id: int | None = None
    category_ids: list[int] = Field(default_factory=list)
    translations: list[TranslationCreate] = Field(min_length=1)
    conjugations: list[ConjugationCreate] = Field(default_factory=list)


class VocabularyUpdate(BaseModel):
    """Replace editable vocabulary fields and their nested learning data."""

    text: str = Field(min_length=1, max_length=500)
    language_id: int
    vocabulary_type_id: int
    chapter_id: int | None = None
    category_ids: list[int] = Field(default_factory=list)
    translations: list[TranslationCreate] = Field(min_length=1)
    conjugations: list[ConjugationCreate] = Field(default_factory=list)


class VocabularyResponse(BaseModel):
    """Return a complete vocabulary card for any interface."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    language: LanguageResponse
    vocabulary_type: ReferenceResponse
    chapter: ReferenceResponse | None
    categories: list[ReferenceResponse]
    translations: list[TranslationResponse]
    verb_conjugations: list[ConjugationResponse]
    created_at: datetime


class VocabularyListResponse(BaseModel):
    """Return a paginated collection of vocabulary cards."""

    items: list[VocabularyResponse]
    total: int
    page: int
    page_size: int


class QuizCreateRequest(BaseModel):
    """Define which complete quiz the backend should generate."""

    source_language_id: int
    target_language_id: int
    category_ids: list[int] = Field(default_factory=list)
    chapter_ids: list[int] = Field(default_factory=list)
    vocabulary_type_ids: list[int] = Field(default_factory=list)
    question_count: int = Field(default=10, ge=1, le=100)
    selection_mode: QuizSelectionMode = QuizSelectionMode.RANDOM
    question_types: list[QuizQuestionType] = Field(
        default_factory=lambda: [QuizQuestionType.TRANSLATION]
    )
    client_type: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def validate_language_direction(self) -> "QuizCreateRequest":
        """Reject a quiz that translates a language into itself."""
        if self.source_language_id == self.target_language_id:
            raise ValueError("Source and target languages must differ")
        return self


class QuizQuestion(BaseModel):
    """Return one self-contained question for local client execution."""

    id: str
    vocabulary_id: int
    type: QuizQuestionType
    prompt: str
    accepted_answers: list[str] | dict[str, list[str]]
    category_ids: list[int]


class QuizResponse(BaseModel):
    """Return a complete quiz and any non-fatal generation warnings."""

    quiz_id: int
    generated_at: datetime
    requested_question_count: int
    actual_question_count: int
    configuration: dict
    warnings: list[str] = Field(default_factory=list)
    questions: list[QuizQuestion]


class QuizAttemptSubmit(BaseModel):
    """Submit a user's answer for one generated question."""

    question_id: str
    answer: str | dict[str, str]
    response_time_ms: int | None = Field(default=None, ge=0)


class QuizResultSubmit(BaseModel):
    """Submit all locally collected answers after the quiz finishes."""

    attempts: list[QuizAttemptSubmit]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    client_type: str | None = Field(default=None, max_length=30)


class AttemptEvaluation(BaseModel):
    """Explain the deterministic evaluation of one submitted answer."""

    question_id: str
    correct: bool
    score: float
    accepted_answers: list[str] | dict[str, list[str]]
    feedback: str


class ScoreResponse(BaseModel):
    """Summarize the numerical result of a completed quiz."""

    correct: int
    incorrect: int
    total: int
    percentage: float


class QuizResultResponse(BaseModel):
    """Return the score, evaluations, and replaceable advice contract."""

    result_id: int
    quiz_id: int
    score: ScoreResponse
    attempts: list[AttemptEvaluation]
    advice: dict
