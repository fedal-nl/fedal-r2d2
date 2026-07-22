import pytest
from fastapi import HTTPException

from src.core.config import get_email_profile, get_settings
from src.core.database import get_db
from src.dependencies.auth import validate_token


def test_settings_are_loaded() -> None:
    settings = get_settings()
    assert settings.database_url
    assert settings.resend_api_key == "re_test"


def test_application_email_profile_is_loaded() -> None:
    profile = get_email_profile("zaansrecht")
    assert profile.resend_api_key == "re_zaansrecht_test"
    assert profile.email_to == "owner@zaansrecht.example"


@pytest.mark.parametrize("application", ["", "../secret", "bad-name", "1app"])
def test_application_email_profile_rejects_invalid_identifiers(application) -> None:
    with pytest.raises(ValueError, match="Invalid email application"):
        get_email_profile(application)


def test_application_email_profile_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY_UNKNOWN", raising=False)
    monkeypatch.delenv("EMAIL_FROM_UNKNOWN", raising=False)
    monkeypatch.delenv("EMAIL_TO_UNKNOWN", raising=False)
    with pytest.raises(ValueError, match="RESEND_API_KEY_UNKNOWN"):
        get_email_profile("unknown")


def test_validate_token() -> None:
    assert validate_token("Bearer api-test-token") is True


def test_validate_token_rejects_invalid_value() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_token("Bearer wrong")
    assert exc_info.value.status_code == 401


def test_database_dependency_closes_session(monkeypatch) -> None:
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    monkeypatch.setattr("src.core.database.SessionLocal", lambda: session)
    dependency = get_db()
    assert next(dependency) is session
    dependency.close()
    assert session.closed is True
