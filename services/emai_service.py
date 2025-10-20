# app/services/email_service.py
import logging
import aiosmtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from models.email_log import EmailLog
import datetime
from enums import EmailStatus
from dotenv import load_dotenv
import os
import exceptions as exceptions

load_dotenv()

logger = logging.getLogger(__name__)

THROTTLE_LIMIT = 3  # max emails per minute
THROTTLE_WINDOW = datetime.timedelta(minutes=1)

class EmailService:
    def __init__(self, db: Session):
        self.db = db
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.from_email = os.getenv("FROM_EMAIL", "")
        self.to_email = os.getenv("TO_EMAIL", "")

    async def _can_send(self) -> bool:
        """Throttle: allow only X emails per minute"""
        one_minute_ago = datetime.datetime.now(datetime.timezone.utc) - THROTTLE_WINDOW
        logger.debug("Checking email send limit since %s", one_minute_ago)

        result = self.db.query(EmailLog).filter(EmailLog.created_at > one_minute_ago).count()
        logger.debug("Email send count in the last minute: %d", result)

        return result < THROTTLE_LIMIT

    async def send_email(self, sender: str, subject: str, content: str):
        """Send an email and log the result."""
        # Throttle check
        if not await self._can_send():
            raise exceptions.EmailRateLimitException("Email send rate limit exceeded.")

        # prepare email
        message = EmailMessage()
        message["From"] = f"{self.from_email}"
        message["To"] = self.to_email
        message["Subject"] = f"Form submit from {sender}: {subject}"
        message["Reply-To"] = sender
        message.set_content(content)

        logger.info("Sending email from %s to %s with subject '%s'", sender, self.to_email, subject)

        # log initial entry
        log_entry = EmailLog(
            sender=sender,
            receiver=self.to_email,
            subject=subject,
            status=EmailStatus.PENDING
        )
        logger.debug("Created email log entry: %s", log_entry)

        # add log entry to the database
        self.db.add(log_entry)
        self.db.commit()

        try:
            # send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_pass,
                start_tls=True
            )
            log_entry.status = EmailStatus.SENT # type: ignore
            logger.info("Email sent successfully from %s to %s", sender, self.to_email)
        except Exception as e:
            log_entry.status = EmailStatus.FAILED # type: ignore
            log_entry.error_message = str(e)  # type: ignore
            logger.error("Failed to send email from %s to %s: %s", sender, self.to_email, e)
            raise exceptions.EmailSendException(f"Failed to send email: {e}")
        finally:
            self.db.add(log_entry)
            logger.debug("Updating email log entry: %s", log_entry)

            # commit the email log entry
            self.db.commit()

    def get_sent_emails(self):
        """Retrieve all sent emails."""
        sent_emails = self.db.query(EmailLog).filter(EmailLog.status == EmailStatus.SENT).all()
        logger.info("Retrieved %d sent emails", len(sent_emails))
        return sent_emails
    
    def get_all_emails(self):
        """Retrieve all emails."""
        all_emails = self.db.query(EmailLog).all()
        logger.info("Retrieved %d total emails", len(all_emails))
        return all_emails

    def get_email_status(self, email_id: int):
        """Retrieve the status of a specific email."""
        email = self.db.query(EmailLog).filter(EmailLog.id == email_id).first()
        if email:
            logger.info("Retrieved status for email_id %d: %s", email_id, email.status)
            return email.status
        logger.warning("Email with id %d not found", email_id)
        return None
