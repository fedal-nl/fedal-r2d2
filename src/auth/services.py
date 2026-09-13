"""Password hashing, JWT issuance, and rotating refresh-session management."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Callable

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
from src.modules.email.service import EmailMessage, EmailService

password_hash = PasswordHash.recommended()


def _unauthorized(detail: str = "Invalid credentials") -> HTTPException:
    """Build a consistent bearer-authentication error response."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 digest persisted instead of a raw refresh token."""
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> uuid.UUID:
    """Validate an access JWT and return its user UUID subject."""
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
    """Manage local user credentials, JWTs, and refreshable login sessions."""

    def __init__(
        self,
        db: Session,
        password_reset_sender: Callable[[str, str], None] | None = None,
    ):
        """Create the service with a database session and optional reset sender."""
        self.db = db
        self.password_reset_sender = password_reset_sender or self._send_password_reset

    def register(self, payload: UserCreate) -> User:
        """Create an active local user with a securely hashed password."""
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
        """Verify local credentials and issue a new access/refresh token pair."""
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
        """Rotate a valid refresh token and return a replacement token pair."""
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
        """Revoke the matching active refresh session when it exists."""
        session = self.db.scalar(
            select(RefreshSession).where(
                RefreshSession.token_hash == hash_refresh_token(raw_token)
            )
        )
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def request_password_reset(self, email: str) -> None:
        """Email a short-lived reset token without revealing account existence."""
        user = self.db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None or not user.is_active or not user.password_hash:
            return
        settings = get_settings()
        if not settings.jwt_secret_key:
            raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
        now = datetime.now(UTC)
        fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest()
        token = jwt.encode(
            {
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "sub": str(user.id),
                "iat": now,
                "exp": now + timedelta(minutes=settings.password_reset_minutes),
                "jti": str(uuid.uuid4()),
                "purpose": "password-reset",
                "password_fingerprint": fingerprint,
            },
            settings.jwt_secret_key,
            algorithm="HS256",
        )
        self.password_reset_sender(str(user.email), token)

    def confirm_password_reset(self, token: str, new_password: str) -> None:
        """Replace the password and revoke all existing refresh sessions."""
        settings = get_settings()
        try:
            claims = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=["HS256"],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "jti"]},
            )
            if claims.get("purpose") != "password-reset":
                raise ValueError("Incorrect token purpose")
            user = self.db.get(User, uuid.UUID(claims["sub"]))
            if user is None or not user.is_active or not user.password_hash:
                raise ValueError("Invalid user")
            fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest()
            if not secrets.compare_digest(
                claims.get("password_fingerprint", ""), fingerprint
            ):
                raise ValueError("Token already used")
        except (InvalidTokenError, ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            ) from exc

        now = datetime.now(UTC)
        user.password_hash = password_hash.hash(new_password)
        sessions = self.db.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user.id,
                RefreshSession.revoked_at.is_(None),
            )
        )
        for session in sessions:
            session.revoked_at = now
        self.db.commit()

    def _send_password_reset(self, email: str, token: str) -> None:
        """Deliver a password-reset token through the Spanglish email profile."""
        EmailService(self.db).send_to(
            EmailMessage(
                application="spanglish",
                reply_to=email,
                subject="Reset your R2D2 password",
                text=(
                    "Use this password reset token in the Spanglish CLI. "
                    f"It expires soon:\n\n{token}"
                ),
            ),
            email,
        )

    def _new_token_pair(self, user: User, client_type: str | None) -> TokenResponse:
        """Issue an access JWT and persist a hashed refresh-session token."""
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
