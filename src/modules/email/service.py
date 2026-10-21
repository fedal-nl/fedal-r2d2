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
        payload: resend.Emails.SendParams = {
            "from": sender,
            "to": [receiver],
            "subject": message.subject,
            "tags": [{"name": "application", "value": message.application}],
        }
        if message.html:
            payload["html"] = message.html
        if message.text:
            payload["text"] = message.text
        logger.debug(
            "Resend payload prepared application=%s has_html=%s has_text=%s "
            "html_length=%s text_length=%s",
            message.application,
            bool(message.html),
            bool(message.text),
            len(message.html or ""),
            len(message.text or ""),
        )
        # The SDK keeps its API key in module-level state. Keep assignment and
        # delivery atomic so concurrent applications cannot exchange keys.
        with _resend_lock:
            logger.debug("Calling Resend API application=%s", message.application)
            resend.api_key = self.api_key
            response = resend.Emails.send(payload)
        logger.debug("Resend API response received application=%s", message.application)
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
        logger.debug(
            "Resolving fixed-recipient email profile application=%s",
            message.application,
        )
        profile: EmailProfile = self.profile_resolver(message.application)
        if not profile.email_to:
            suffix = (
                ""
                if message.application == "general"
                else f"_{message.application.upper()}"
            )
            raise ValueError(f"Missing fixed email recipient: EMAIL_TO{suffix}")
        return self._send(message, profile, profile.email_to)

    def send_to(self, message: EmailMessage, receiver: str) -> EmailLog:
        """Send application email to an explicitly selected recipient."""
        logger.debug(
            "Resolving dynamic-recipient email profile application=%s",
            message.application,
        )
        profile: EmailProfile = self.profile_resolver(message.application)
        return self._send(message, profile, receiver)

    def _send(
        self, message: EmailMessage, profile: EmailProfile, receiver: str
    ) -> EmailLog:
        provider = self.provider or ResendEmailProvider(profile.resend_api_key)

        log = EmailLog(
            application=message.application,
            sender=profile.email_from,
            receiver=receiver,
            subject=message.subject,
            body=message.html or message.text,
            status=EmailStatus.SENDING,
        )
        self.db.add(log)
        self.db.flush()

        logger.debug(
            "Email audit row created application=%s email_log_id=%s "
            "provider=%s delivery_mode=%s",
            message.application,
            log.id,
            type(provider).__name__,
            "custom" if self.provider is not None else "resend",
        )

        logger.info(
            "Email delivery started application=%s email_log_id=%s",
            message.application,
            log.id,
        )

        try:
            log.provider_message_id = provider.send(
                sender=profile.email_from,
                receiver=receiver,
                message=message,
            )
            log.status = EmailStatus.SENT
            logger.info(
                "Email delivery succeeded application=%s email_log_id=%s "
                "provider_message_id=%s",
                message.application,
                log.id,
                log.provider_message_id,
            )
        except Exception as exc:
            log.status = EmailStatus.FAILED
            log.error_message = str(exc)
            logger.exception(
                "Email delivery failed application=%s email_log_id=%s",
                message.application,
                log.id,
            )

        self.db.commit()
        self.db.refresh(log)
        logger.debug(
            "Email audit row persisted application=%s email_log_id=%s status=%s",
            message.application,
            log.id,
            log.status,
        )
        return log

    def get_by_status(self, status: EmailStatus) -> list[EmailLog]:
        return self.db.query(EmailLog).filter(EmailLog.status == status).all()

    def get_all(self) -> list[EmailLog]:
        return self.db.query(EmailLog).all()

    def get_status(self, email_id: int) -> str | None:
        email = self.db.query(EmailLog).filter(EmailLog.id == email_id).first()
        return email.status if email else None
