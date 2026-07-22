from src.core.config import EmailProfile
from src.enums import EmailStatus
from src.modules.email.service import EmailMessage, EmailService
from src.modules.email.service import ResendEmailProvider


class FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.added[-1].id = 42

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        return None

    def query(self, model):
        return FakeQuery(self.added)


class FakeQuery:
    def __init__(self, values):
        self.values = values

    def filter(self, *args):
        return self

    def all(self):
        return self.values

    def first(self):
        return self.values[0] if self.values else None


class SuccessfulProvider:
    def send(self, *, sender, receiver, message):
        assert sender == "R2D2 <noreply@example.com>"
        assert receiver == "owner@example.com"
        assert message.application == "spanglish"
        return "resend-message-id"


class FailedProvider:
    def send(self, **kwargs):
        raise RuntimeError("provider unavailable")


PROFILE = EmailProfile(
    application="spanglish",
    resend_api_key="re_test",
    email_from="R2D2 <noreply@example.com>",
    email_to="owner@example.com",
)


def profile_resolver(application):
    assert application == "spanglish"
    return PROFILE


MESSAGE = EmailMessage(
    application="spanglish",
    reply_to="visitor@example.com",
    subject="Contact",
    text="Hello",
)


def test_send_records_resend_success() -> None:
    session = FakeSession()
    log = EmailService(session, SuccessfulProvider(), profile_resolver).send(MESSAGE)
    assert log.status == EmailStatus.SENT
    assert log.provider_message_id == "resend-message-id"
    assert log.application == "spanglish"
    assert session.commits == 1


def test_send_records_resend_failure_without_losing_log() -> None:
    session = FakeSession()
    log = EmailService(session, FailedProvider(), profile_resolver).send(MESSAGE)
    assert log.status == EmailStatus.FAILED
    assert log.error_message == "provider unavailable"
    assert session.commits == 1


def test_send_uses_application_specific_profile() -> None:
    class RecipientProvider(SuccessfulProvider):
        def send(self, *, sender, receiver, message):
            assert receiver == "owner@example.com"
            return "custom-id"

    log = EmailService(FakeSession(), RecipientProvider(), profile_resolver).send(MESSAGE)
    assert log.receiver == "owner@example.com"


def test_email_queries() -> None:
    session = FakeSession()
    log = EmailService(session, SuccessfulProvider(), profile_resolver).send(MESSAGE)
    service = EmailService(session, SuccessfulProvider(), profile_resolver)
    assert service.get_by_status(EmailStatus.SENT) == [log]
    assert service.get_all() == [log]
    assert service.get_status(log.id) == EmailStatus.SENT


def test_email_status_returns_none_when_missing() -> None:
    service = EmailService(FakeSession(), SuccessfulProvider(), profile_resolver)
    assert service.get_status(999) is None


def test_resend_provider(monkeypatch) -> None:
    sent = {}

    def fake_send(payload):
        sent.update(payload)
        return {"id": "resend-id"}

    monkeypatch.setattr("resend.Emails.send", fake_send)
    provider = ResendEmailProvider("re_test")
    assert provider.send(
        sender=PROFILE.email_from,
        receiver=PROFILE.email_to,
        message=MESSAGE,
    ) == "resend-id"
    assert sent["tags"] == [{"name": "application", "value": "spanglish"}]


def test_resend_provider_requires_api_key() -> None:
    import pytest

    with pytest.raises(ValueError, match="RESEND_API_KEY"):
        ResendEmailProvider("")


def test_html_body_is_sent_and_logged() -> None:
    sent = {}

    class HtmlProvider:
        def send(self, *, sender, receiver, message):
            sent["html"] = message.html
            return "html-id"

    message = EmailMessage(
        application="spanglish",
        reply_to="visitor@example.com",
        subject="HTML message",
        html="<h1>Hello</h1>",
    )
    log = EmailService(FakeSession(), HtmlProvider(), profile_resolver).send(message)
    assert sent["html"] == "<h1>Hello</h1>"
    assert log.body == "<h1>Hello</h1>"
