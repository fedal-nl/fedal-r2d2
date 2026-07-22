from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.enums import EmailStatus, FormStatus
from src.modules.email import routers as email_routers
from src.modules.email.schemas import EmailSendRequest
from src.modules.forms import routers as form_routers
from src.modules.forms.schemas import FormStatusUpdate, ZaansrechtFormCreate


def request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )


def test_email_router_functions(monkeypatch) -> None:
    class FakeEmailService:
        def __init__(self, db):
            pass

        def send(self, message):
            return SimpleNamespace(id=1, status=EmailStatus.SENT)

        def get_by_status(self, status):
            return [status]

        def get_status(self, email_id):
            return EmailStatus.SENT if email_id == 1 else None

        def get_all(self):
            return ["email"]

    monkeypatch.setattr(email_routers, "EmailService", FakeEmailService)
    payload = EmailSendRequest(
        application="spanglish",
        reply_to="reply@example.com",
        subject="Subject",
        html="<p>Body</p>",
    )
    assert email_routers.send_email_route(payload, object(), True) == {
        "id": 1,
        "status": EmailStatus.SENT,
    }
    assert email_routers.get_sent_emails(object(), EmailStatus.SENT) == [EmailStatus.SENT]
    assert email_routers.get_email_status(1, object())["status"] == EmailStatus.SENT
    assert email_routers.get_all_emails(object()) == {"all_emails": ["email"]}
    with pytest.raises(HTTPException) as exc_info:
        email_routers.get_email_status(2, object())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_form_router(monkeypatch) -> None:
    created = SimpleNamespace(id=4)

    class FakeFormService:
        def __init__(self, db):
            pass

        def create_zaansrecht_form(self, **kwargs):
            return created

        def send_form_notification(self, form):
            return None

    class FakeLogService:
        def __init__(self, *args, **kwargs):
            pass

        def log_form_submission(self):
            return None

    monkeypatch.setattr(form_routers, "FormService", FakeFormService)
    monkeypatch.setattr(form_routers, "FormSubmissionLogService", FakeLogService)
    payload = ZaansrechtFormCreate(
        full_name="Test",
        email="test@example.com",
        terms_accepted=True,
    )
    assert await form_routers.create_zaansrecht_form(
        request(), payload, object(), "captcha-token"
    ) is created


@pytest.mark.asyncio
async def test_create_form_router_translates_failure(monkeypatch) -> None:
    class FailedFormService:
        def __init__(self, db):
            pass

        def create_zaansrecht_form(self, **kwargs):
            raise RuntimeError("failed")

    monkeypatch.setattr(form_routers, "FormService", FailedFormService)
    payload = ZaansrechtFormCreate(
        full_name="Test",
        email="test@example.com",
        terms_accepted=True,
    )
    with pytest.raises(HTTPException) as exc_info:
        await form_routers.create_zaansrecht_form(
            request(), payload, object(), "captcha-token"
        )
    assert exc_info.value.status_code == 500


def test_form_list_and_status_routes(monkeypatch) -> None:
    form = SimpleNamespace(
        id=1,
        full_name="Test",
        email="test@example.com",
        status=FormStatus.NEW,
        created_at="2026-01-01T00:00:00Z",
        updated_at=None,
        terms_accepted=True,
        telephone=None,
        description=None,
        subject=None,
        meeting_datetime=None,
        meeting_type=None,
    )

    class FakeFormService:
        missing = False

        def __init__(self, db):
            pass

        def get_forms_by_status_or_all(self, status):
            return [form]

        def update_form_status(self, form_id, status):
            return None if self.missing else form

    monkeypatch.setattr(form_routers, "FormService", FakeFormService)
    result = form_routers.get_forms(request(), object(), FormStatus.NEW)
    assert len(result.forms) == 1
    assert form_routers.update_form_status(
        1, FormStatusUpdate(new_status=FormStatus.NEW), object()
    ) is form
    FakeFormService.missing = True
    with pytest.raises(HTTPException) as exc_info:
        form_routers.update_form_status(
            999, FormStatusUpdate(new_status=FormStatus.NEW), object()
        )
    assert exc_info.value.status_code == 404
