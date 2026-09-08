"""Password hashing, JWT issuance, and rotating refresh-session management."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.auth.models import RefreshSession, User
from src.auth.schemas import TokenResponse, UserCreate
from src.core.config import get_settings

password_hash = PasswordHash.recommended()


def _unauthorized(detail: str = "Invalid credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
        )
        return uuid.UUID(claims["sub"])
    except (InvalidTokenError, ValueError, KeyError) as exc:
        raise _unauthorized("Invalid or expired access token") from exc


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: UserCreate) -> User:
        user = User(
            username=payload.username.strip(),
            email=str(payload.email).strip().lower(),
            password_hash=password_hash.hash(payload.password),
            avatar_url=str(payload.avatar_url) if payload.avatar_url else None,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=409, detail="Username or email is already registered"
            ) from exc
        self.db.refresh(user)
        return user

    def login(
        self, email: str, password: str, client_type: str | None
    ) -> TokenResponse:
        normalized = email.strip().lower()
        user = self.db.scalar(
            select(User).where(or_(User.email == normalized, User.username == email))
        )
        if (
            user is None
            or not user.is_active
            or not user.password_hash
            or not password_hash.verify(password, user.password_hash)
        ):
            raise _unauthorized()
        user.last_login_at = datetime.now(UTC)
        return self._new_token_pair(user, client_type)

    def refresh(self, raw_token: str) -> TokenResponse:
        now = datetime.now(UTC)
        session = self.db.scalar(
            select(RefreshSession)
            .where(RefreshSession.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )
        if (
            session is None
            or session.revoked_at is not None
            or session.expires_at <= now
            or not session.user.is_active
        ):
            raise _unauthorized("Invalid or expired refresh token")
        session.revoked_at = now
        session.last_used_at = now
        return self._new_token_pair(session.user, session.client_type)

    def logout(self, raw_token: str) -> None:
        session = self.db.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == hash_refresh_token(raw_token)
            )
        )
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def _new_token_pair(self, user: User, client_type: str | None) -> TokenResponse:
        settings = get_settings()
        if not settings.jwt_secret_key:
            raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=settings.access_token_minutes)
        access_token = jwt.encode(
            {
                "iss": settings.jwt_issuer,
                "sub": str(user.id),
                "aud": settings.jwt_audience,
                "iat": now,
                "exp": expires,
                "jti": str(uuid.uuid4()),
                "scope": "spanglish:read spanglish:write",
            },
            settings.jwt_secret_key,
            algorithm="HS256",
        )
        refresh_token = secrets.token_urlsafe(48)
        self.db.add(
            RefreshSession(
                user_id=user.id,
                token_hash=hash_refresh_token(refresh_token),
                client_type=client_type,
                expires_at=now + timedelta(days=settings.refresh_token_days),
            )
        )
        self.db.commit()
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_minutes * 60,
        )
