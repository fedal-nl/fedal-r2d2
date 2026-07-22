import logging
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

import resend
from sqlalchemy.orm import Session

from src.core.config import EmailProfile, get_email_profile
from src.enums import EmailStatus
from src.modules.email.models import EmailLog

logger = logging.getLogger(__name__)
_resend_lock = Lock()


@dataclass(frozen=True)
class EmailMessage:
    application: str
    reply_to: str
    subject: str
    text: str | None = None
    html: str | None = None


class EmailProvider(Protocol):
    def send(self, *, sender: str, receiver: str, message: EmailMessage) -> str: ...


class ResendEmailProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("RESEND_API_KEY environment variable is not set")
        self.api_key = api_key

    def send(self, *, sender: str, receiver: str, message: EmailMessage) -> str:
        payload = {
            "from": sender,
            "to": [receiver],
            "subject": message.subject,
            "reply_to": message.reply_to,
            "tags": [{"name": "application", "value": message.application}],
        }
        if message.html:
            payload["html"] = message.html
        if message.text:
            payload["text"] = message.text
        # The SDK keeps its API key in module-level state. Keep assignment and
        # delivery atomic so concurrent applications cannot exchange keys.
        with _resend_lock:
            resend.api_key = self.api_key
            response = resend.Emails.send(payload)
        return str(response["id"])


class EmailService:
    def __init__(
        self,
        db: Session,
        provider: EmailProvider | None = None,
        profile_resolver=get_email_profile,
    ):
        self.db = db
        self.provider = provider
        self.profile_resolver = profile_resolver

    def send(self, message: EmailMessage) -> EmailLog:
        profile: EmailProfile = self.profile_resolver(message.application)
        provider = self.provider or ResendEmailProvider(profile.resend_api_key)

        log = EmailLog(
            application=message.application,
            sender=message.reply_to,
            receiver=profile.email_to,
            subject=message.subject,
            body=message.html or message.text,
            status=EmailStatus.SENDING,
        )
        self.db.add(log)
        self.db.flush()

        try:
            log.provider_message_id = provider.send(
                sender=profile.email_from,
                receiver=profile.email_to,
                message=message,
            )
            log.status = EmailStatus.SENT
        except Exception as exc:
            log.status = EmailStatus.FAILED
            log.error_message = str(exc)
            logger.exception("Resend failed for %s email log %s", message.application, log.id)

        self.db.commit()
        self.db.refresh(log)
        return log

    def get_by_status(self, status: EmailStatus) -> list[EmailLog]:
        return self.db.query(EmailLog).filter(EmailLog.status == status).all()

    def get_all(self) -> list[EmailLog]:
        return self.db.query(EmailLog).all()

    def get_status(self, email_id: int) -> str | None:
        email = self.db.query(EmailLog).filter(EmailLog.id == email_id).first()
        return email.status if email else None
