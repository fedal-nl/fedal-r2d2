"""Local authentication HTTP routes shared by CLI and graphical clients."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from src.auth import schemas
from src.auth.models import User
from src.auth.services import AuthService
from src.core.database import get_db
from src.dependencies.auth import get_current_user

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED
)
def register(
    payload: schemas.UserCreate,
    service: AuthService = Depends(get_auth_service),
):
    return service.register(payload)


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.login(str(payload.email), payload.password, payload.client_type)


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(
    payload: schemas.RefreshRequest,
    service: AuthService = Depends(get_auth_service),
):
    return service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: schemas.LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    service.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=schemas.UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
