# app/cron/send_email.py
import asyncio
import logging
from sqlalchemy.orm import Session
from configs.db import get_db as get_db_session
from services.emai_service import EmailService
from models.email_log import EmailLog
from enums import EmailStatus

logger = logging.getLogger(__name__)

async def send_queued_emails(db: Session = None):
    """Send all queued emails."""
    close_db = False
    if db is None:
        db = get_db_session()
        close_db = True
    try:
        email_service = EmailService(db)
        queued_emails = db.query(EmailLog).filter(EmailLog.status == EmailStatus.QUEUED).all()

        logger.info("Cronjob: Found %d queued emails to send", len(queued_emails))

        for email in queued_emails:
            try:
                logger.info("Cronjob: Sending queued email ID %d", email.id)
                await email_service.send_email(email_log=email)
                logger.info("Cronjob: Processed queued email ID %d", email.id)
            except Exception as e:
                logger.error("Cronjob: Failed to send queued email ID %d: %s", email.id, str(e))

        logger.info("Cronjob: Completed processing queued emails")
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    asyncio.run(send_queued_emails())
