from datetime import datetime

from src.enums import FormStatus
from src.modules.forms.models import ZaansrechtForm
from src.modules.forms.service import FormService, FormSubmissionLogService


class FakeQuery:
    def __init__(self, values):
        self.values = values

    def filter(self, *args):
        return self

    def all(self):
        return self.values

    def first(self):
        return self.values[0] if self.values else None


class FakeSession:
    def __init__(self, values=None, fail=False):
        self.values = values or []
        self.fail = fail
        self.added = []
        self.commits = 0
        self.rolled_back = False

    def add(self, value):
        if self.fail:
            raise RuntimeError("database unavailable")
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        if getattr(value, "id", None) is None:
            value.id = 7

    def query(self, model):
        return FakeQuery(self.values)

    def rollback(self):
        self.rolled_back = True


def test_forwarded_for_is_normalized() -> None:
    service = FormSubmissionLogService(db=None, form_id=1)
    assert service._filter_x_forwarded_for("192.0.2.1, 198.51.100.2") == [
        "192.0.2.1",
        "198.51.100.2",
    ]


def test_captcha_token_is_redacted_for_audit_log() -> None:
    service = FormSubmissionLogService(db=None, form_id=1)
    assert service._shorten_captcha_token("abcdefghijklmno") == "abcde...klmno"


def test_short_values_and_missing_forwarded_for_are_preserved() -> None:
    service = FormSubmissionLogService(db=None, form_id=1)
    assert service._filter_x_forwarded_for(None) == []
    assert service._shorten_captcha_token("short") == "short"


def test_create_and_query_forms() -> None:
    session = FakeSession()
    service = FormService(session)
    form = service.create_zaansrecht_form(
        full_name="Test User",
        email="test@example.com",
        terms_accepted=True,
    )
    assert form.id == 7
    assert form.status == FormStatus.NEW

    session.values = [form]
    assert service.get_forms_by_status_or_all() == [form]
    assert service.get_forms_by_status_or_all(FormStatus.NEW) == [form]


def test_update_form_status_and_missing_form() -> None:
    form = ZaansrechtForm(full_name="Test", email="test@example.com", terms_accepted=True)
    session = FakeSession([form])
    service = FormService(session)
    assert service.update_form_status(1, FormStatus.ARCHIVED).status == FormStatus.ARCHIVED
    session.values = []
    assert service.update_form_status(999, FormStatus.VIEWED) is None


def test_submission_log_success_and_failure() -> None:
    session = FakeSession()
    result = FormSubmissionLogService(
        session,
        form_id=1,
        x_forwarded_for="192.0.2.1",
        captcha_token="abcdefghijklmno",
    ).log_form_submission()
    assert result.id == 7
    assert result.captcha_token == "abcde...klmno"

    failed_session = FakeSession(fail=True)
    assert FormSubmissionLogService(failed_session, form_id=1).log_form_submission() is None
    assert failed_session.rolled_back is True


def test_form_notification_uses_general_email_service(monkeypatch) -> None:
    captured = {}

    class FakeEmailService:
        def __init__(self, db):
            pass

        def send(self, message):
            captured["message"] = message
            return type("Log", (), {"id": 12})()

    monkeypatch.setattr("src.modules.forms.service.EmailService", FakeEmailService)
    form = ZaansrechtForm(
        id=1,
        full_name="Test <script>alert('x')</script>",
        email="reply@example.com",
        terms_accepted=True,
        telephone="06-12345678",
        subject="Question",
        description="A clear description",
        meeting_datetime=datetime(2026, 7, 24, 14, 30),
        meeting_type="virtual",
    )
    log = FormService(FakeSession()).send_form_notification(form)
    assert log.id == 12
    message = captured["message"]
    assert message.application == "zaansrecht"
    assert message.html is not None
    assert "Verdana, Geneva, sans-serif" in message.html
    assert "Test &lt;script&gt;" in message.html
    assert "<script>alert" not in message.html
    for expected in (
        "Naam",
        "E-mailadres",
        "Telefoon",
        "Onderwerp",
        "Beschrijving",
        "Afspraak",
        "Type afspraak",
        "Voorwaarden geaccepteerd",
        "24-07-2026 14:30",
        "06-12345678",
        "A clear description",
        "virtual",
        "Ja",
    ):
        assert expected in message.html
    assert "Naam: Test" in message.text
