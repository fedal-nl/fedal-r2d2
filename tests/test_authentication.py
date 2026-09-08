"""Unit tests for local authentication and the shared user dependency."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError

from src.auth import routers, schemas
from src.auth.models import RefreshSession, User
from src.auth.services import AuthService, decode_access_token, hash_refresh_token
from src.dependencies.auth import get_current_user

USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def user(**overrides) -> User:
    values = {
        "id": USER_ID,
        "username": "cli-user",
        "email": "cli@example.com",
        "password_hash": None,
        "is_active": True,
        "created_at": datetime.now(UTC),
        "last_login_at": None,
    }
    values.update(overrides)
    return User(**values)


def test_register_hashes_password_and_rejects_duplicate() -> None:
    db = MagicMock()
    service = AuthService(db)
    payload = schemas.UserCreate(
        username="cli-user", email="CLI@example.com", password="correct-horse"
    )
    created = service.register(payload)
    assert created.email == "cli@example.com"
    assert created.password_hash != payload.password
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    with pytest.raises(HTTPException) as error:
        service.register(payload)
    assert error.value.status_code == 409
    db.rollback.assert_called_once()


def test_login_access_token_and_current_user() -> None:
    db = MagicMock()
    service = AuthService(db)
    created = service.register(
        schemas.UserCreate(
            username="cli-user", email="cli@example.com", password="correct-horse"
        )
    )
    created.id = USER_ID
    created.is_active = True
    db.scalar.return_value = created
    tokens = service.login("CLI@example.com", "correct-horse", "cli")
    assert tokens.token_type == "bearer"
    assert decode_access_token(tokens.access_token) == USER_ID
    assert isinstance(db.add.call_args.args[0], RefreshSession)

    db.get.return_value = created
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=tokens.access_token
    )
    assert get_current_user(credentials, db) is created


@pytest.mark.parametrize(
    "candidate",
    [None, user(is_active=False), user(password_hash=None)],
)
def test_login_rejects_invalid_accounts(candidate) -> None:
    db = MagicMock()
    db.scalar.return_value = candidate
    with pytest.raises(HTTPException) as error:
        AuthService(db).login("cli@example.com", "wrong-password", "cli")
    assert error.value.status_code == 401


def test_refresh_rotates_and_logout_revokes() -> None:
    db = MagicMock()
    account = user()
    session = RefreshSession(
        user_id=USER_ID,
        token_hash=hash_refresh_token("r" * 40),
        client_type="cli",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session.user = account
    db.scalar.return_value = session
    service = AuthService(db)
    replacement = service.refresh("r" * 40)
    assert replacement.refresh_token != "r" * 40
    assert session.revoked_at is not None

    session.revoked_at = None
    service.logout("r" * 40)
    assert session.revoked_at is not None
    db.scalar.return_value = None
    service.logout("missing" * 8)


@pytest.mark.parametrize(
    "session",
    [
        None,
        SimpleNamespace(revoked_at=datetime.now(UTC)),
        SimpleNamespace(
            revoked_at=None,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ),
    ],
)
def test_refresh_rejects_invalid_session(session) -> None:
    db = MagicMock()
    db.scalar.return_value = session
    with pytest.raises(HTTPException):
        AuthService(db).refresh("r" * 40)


def test_invalid_access_token_and_user_dependency() -> None:
    with pytest.raises(HTTPException):
        decode_access_token("not-a-jwt")
    db = MagicMock()
    with pytest.raises(HTTPException):
        get_current_user(None, db)
    with pytest.raises(HTTPException):
        get_current_user(
            HTTPAuthorizationCredentials(scheme="Basic", credentials="abc"), db
        )


def test_auth_route_wrappers_delegate() -> None:
    service = MagicMock()
    payload = schemas.UserCreate(
        username="cli-user", email="cli@example.com", password="correct-horse"
    )
    routers.register(payload, service)
    login = schemas.LoginRequest(
        email="cli@example.com", password="correct-horse", client_type="cli"
    )
    routers.login(login, service)
    refresh = schemas.RefreshRequest(refresh_token="r" * 40)
    routers.refresh(refresh, service)
    assert (
        routers.logout(
            schemas.LogoutRequest(**refresh.model_dump()), service
        ).status_code
        == 204
    )
    account = user()
    assert routers.me(account) is account
    assert routers.get_auth_service(service).db is service
