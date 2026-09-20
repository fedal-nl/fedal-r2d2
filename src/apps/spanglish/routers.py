"""HTTP routes for the Spanglish application."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.apps.spanglish import schemas
from src.apps.spanglish.repositories import SpanglishRepository
from src.apps.spanglish.services import SpanglishService
from src.core.database import get_db
from src.auth.models import User
from src.dependencies.auth import get_current_user

router = APIRouter()


def get_repository(db: Session = Depends(get_db)) -> SpanglishRepository:
    """Create the request-scoped Spanglish repository."""
    return SpanglishRepository(db)


def get_service(
    repository: SpanglishRepository = Depends(get_repository),
) -> SpanglishService:
    """Create the request-scoped Spanglish business service."""
    return SpanglishService(repository)


@router.get("/quiz-options", response_model=schemas.QuizOptionsResponse)
def get_quiz_options(
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Return selectable languages, categories, types, and quiz modes."""
    return service.get_quiz_options(current_user.id)


@router.get("/languages", response_model=list[schemas.LanguageResponse])
def list_languages(
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """List languages available to vocabulary and quiz clients."""
    repository.ensure_user_references(current_user.id)
    return repository.list_languages(current_user.id)


@router.post("/languages", response_model=schemas.LanguageResponse, status_code=201)
def create_language(
    payload: schemas.LanguageCreate,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """Create a language owned by the authenticated user."""
    return repository.create_language(payload.name, payload.code, current_user.id)


@router.get("/categories", response_model=list[schemas.ReferenceResponse])
def list_categories(
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """List category cards in stable display order."""
    repository.ensure_user_references(current_user.id)
    return repository.list_categories(current_user.id)


@router.post("/categories", response_model=schemas.ReferenceResponse, status_code=201)
def create_category(
    payload: schemas.ReferenceCreate,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """Create a category used to filter vocabulary and quizzes."""
    return repository.create_category(payload.name, current_user.id)


@router.get("/chapters", response_model=list[schemas.ReferenceResponse])
def list_chapters(
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """List optional chapters available to vocabulary and quiz clients."""
    repository.ensure_user_references(current_user.id)
    return repository.list_chapters(current_user.id)


@router.post("/chapters", response_model=schemas.ReferenceResponse, status_code=201)
def create_chapter(
    payload: schemas.ReferenceCreate,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """Create a chapter that may group vocabulary and quizzes."""
    return repository.create_chapter(payload.name, current_user.id)


@router.get("/artists", response_model=list[schemas.ReferenceResponse])
def list_artists(
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """List the authenticated user's artists."""
    return repository.list_artists(current_user.id)


@router.post("/artists", response_model=schemas.ReferenceResponse, status_code=201)
def create_artist(
    payload: schemas.ReferenceCreate,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """Create a performer for the authenticated user."""
    try:
        return repository.create_artist(payload.name, current_user.id)
    except IntegrityError as exc:
        repository.db.rollback()
        raise HTTPException(status_code=409, detail="Artist already exists") from exc


@router.get("/songs", response_model=list[schemas.SongResponse])
def list_songs(
    artist_id: int | None = None,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """List the authenticated user's songs, optionally by artist."""
    return repository.list_songs(current_user.id, artist_id)


@router.post("/songs", response_model=schemas.SongResponse, status_code=201)
def create_song(
    payload: schemas.SongCreate,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """Create a title under one of the authenticated user's artists."""
    if repository.get_artist(payload.artist_id, current_user.id) is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    try:
        return repository.create_song(payload.title, payload.artist_id, current_user.id)
    except IntegrityError as exc:
        repository.db.rollback()
        raise HTTPException(
            status_code=409, detail="Song already exists for this artist"
        ) from exc


@router.post("/vocabulary", response_model=schemas.VocabularyResponse, status_code=201)
def create_vocabulary(
    payload: schemas.VocabularyCreate,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Create a complete vocabulary card owned by the authenticated user."""
    return service.create_vocabulary(payload, current_user.id)


@router.get("/vocabulary", response_model=schemas.VocabularyListResponse)
def list_vocabulary(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    language_id: int | None = None,
    category_id: int | None = None,
    chapter_id: int | None = None,
    randomize: bool = False,
    search: str | None = Query(default=None, max_length=100),
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """List filtered vocabulary cards with pagination metadata."""
    items, total = repository.list_vocabulary(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        language_id=language_id,
        category_id=category_id,
        chapter_id=chapter_id,
        search=search,
        randomize=randomize,
    )
    response_items = [schemas.VocabularyResponse.model_validate(item) for item in items]
    return schemas.VocabularyListResponse(
        items=response_items, total=total, page=page, page_size=page_size
    )


@router.get("/vocabulary/{vocabulary_id}", response_model=schemas.VocabularyResponse)
def get_vocabulary(
    vocabulary_id: int,
    repository: SpanglishRepository = Depends(get_repository),
    current_user: User = Depends(get_current_user),
):
    """Return one complete vocabulary card by identifier."""
    vocabulary = repository.get_vocabulary(vocabulary_id, current_user.id)
    if vocabulary is None:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    return vocabulary


@router.put("/vocabulary/{vocabulary_id}", response_model=schemas.VocabularyResponse)
def update_vocabulary(
    vocabulary_id: int,
    payload: schemas.VocabularyUpdate,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Replace a vocabulary card and its translations and conjugations."""
    return service.update_vocabulary(vocabulary_id, payload, current_user.id)


@router.delete("/vocabulary/{vocabulary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vocabulary(
    vocabulary_id: int,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete a vocabulary card and return an empty success response."""
    service.delete_vocabulary(vocabulary_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/vocabulary/{vocabulary_id}/conjugations",
    response_model=list[schemas.ConjugationResponse],
)
def list_conjugations(
    vocabulary_id: int,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """List all conjugations belonging to one vocabulary item."""
    conjugations = service.list_conjugations(vocabulary_id, current_user.id)
    return [schemas.ConjugationResponse.model_validate(item) for item in conjugations]


@router.post(
    "/vocabulary/{vocabulary_id}/conjugations",
    response_model=schemas.ConjugationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conjugation(
    vocabulary_id: int,
    payload: schemas.ConjugationCreate,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Add one tense, mood, pronoun, and form to existing vocabulary."""
    return service.create_conjugation(vocabulary_id, payload, current_user.id)


@router.put(
    "/vocabulary/{vocabulary_id}/conjugations/{conjugation_id}",
    response_model=schemas.ConjugationResponse,
)
def update_conjugation(
    vocabulary_id: int,
    conjugation_id: int,
    payload: schemas.ConjugationUpdate,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Replace one conjugation while enforcing vocabulary ownership."""
    return service.update_conjugation(
        vocabulary_id, conjugation_id, payload, current_user.id
    )


@router.delete(
    "/vocabulary/{vocabulary_id}/conjugations/{conjugation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conjugation(
    vocabulary_id: int,
    conjugation_id: int,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete one conjugation while leaving its vocabulary item intact."""
    service.delete_conjugation(vocabulary_id, conjugation_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/quizzes", response_model=schemas.QuizResponse, status_code=201)
def create_quiz(
    payload: schemas.QuizCreateRequest,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Generate and return an entire locally executable quiz."""
    return service.generate_quiz(payload, current_user.id)


@router.get("/quizzes/results", response_model=list[schemas.QuizHistoryItem])
def list_quiz_results(
    limit: int = Query(default=5, ge=1, le=100),
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's most recent completed quiz scores."""
    return service.list_quiz_results(current_user.id, limit)


@router.post("/quizzes/{quiz_id}/results", response_model=schemas.QuizResultResponse)
def submit_quiz_result(
    quiz_id: int,
    payload: schemas.QuizResultSubmit,
    service: SpanglishService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Evaluate and store every answer after a client completes a quiz."""
    return service.submit_result(quiz_id, payload, current_user.id)
