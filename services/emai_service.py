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

    # TODO: implement proper throttling mechanism
    async def _can_send(self) -> bool:
        """Throttle: allow only X emails per minute"""
        one_minute_ago = datetime.datetime.now(datetime.timezone.utc) - THROTTLE_WINDOW
        logger.debug("Checking email send limit since %s", one_minute_ago)

        result = self.db.query(EmailLog).filter(EmailLog.created_at > one_minute_ago).count()
        logger.debug("Email send count in the last minute: %d", result)

        return result < THROTTLE_LIMIT

    async def send_email(self, email_log: EmailLog):
        """Send an email and log the result."""
        # Throttle check
        logger.debug("Performing throttle check before sending email with id %d", email_log.id)
        if not await self._can_send():
            raise exceptions.EmailRateLimitException("Email send rate limit exceeded.")

        logger.info("Preparing to send email with id %d", email_log.id)
        try:
            # prepare email
            message = EmailMessage()
            message["From"] = f"{self.from_email}"
            message["To"] = self.to_email
            message["Subject"] = f"Form submit from {email_log.sender}: {email_log.subject}"
            message["Reply-To"] = email_log.sender
            message.set_content(email_log.body or "")

            logger.info("Sending email id %d", email_log.id)
            email_log.status = EmailStatus.SENDING
            # log initial entry

            # send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_pass,
                start_tls=True
            )
            email_log.status = EmailStatus.SENT
            logger.info("Email ID: %d sent successfully", email_log.id)
        except Exception as e:
            email_log.status = EmailStatus.FAILED
            email_log.error_message = str(e)  # type: ignore
            logger.error("Failed to send email ID %d: %s", email_log.id, e)
            raise exceptions.EmailSendException(f"Failed to send email: {e}")
        finally:
            self.db.add(email_log)
            logger.debug("Updating email log entry: %s", email_log.__dict__)
            self.db.commit()
            logger.debug("Finalized email ID: %s", email_log.id)

    def get_sent_emails_by_status(self, status: EmailStatus):
        """Retrieve all sent emails by status."""
        sent_emails = self.db.query(EmailLog).filter(EmailLog.status == status).all()
        logger.info("Retrieved %d sent emails with status %s", len(sent_emails), status)
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

    def queue_new_email_log(self, sender: str, subject: str, message: str):
        """Save a new email log entry with the status to Pending. This will be used before sending the email. by a queue system."""
        log_entry = EmailLog(
            body=message,
            sender=sender,
            receiver=self.to_email,
            subject=subject,
            status=EmailStatus.QUEUED,
            error_message=None
        )
        self.db.add(log_entry)
        self.db.commit()
        logger.info("Stored email log entry: %s with message: %s", log_entry, message)
        return log_entry
