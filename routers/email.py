# app/routers/email.py
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from configs.db import get_db

from services.emai_service import EmailService
from enums import EmailStatus
from dependencies.auth import validate_token
from crons.send_email import send_queued_emails

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/send-email")
async def send_email_route(
    background_tasks: BackgroundTasks,
    sender: str,
    subject: str,
    message: str,
    db: Session = Depends(get_db),
    authorization: str = Depends(validate_token)
):
    """Endpoint to save an email asynchronously in the database with a pending status."""
    email_service = EmailService(db)

    # Schedule the email saving task
    background_tasks.add_task(
        email_service.queue_new_email_log, sender, subject, message
    )

    logger.info("Email saved for %s", sender)

    return {"status": "Email queued for sending"}

@router.get("/sent-emails")
async def get_sent_emails(db: Session = Depends(get_db), status: EmailStatus = EmailStatus.SENT):
    email_service = EmailService(db)
    emails = email_service.get_sent_emails_by_status(status)
    return emails

@router.get("/email-status/{email_id}")
async def get_email_status(email_id: int, db: Session = Depends(get_db)):
    email_service = EmailService(db)
    status = email_service.get_email_status(email_id)
    return {"email_id": email_id, "status": status}

@router.get("/all-emails")
async def get_all_emails(db: Session = Depends(get_db)):
    """Retrieve all emails."""
    email_service = EmailService(db)
    all_emails = email_service.get_all_emails()
    return {"all_emails": all_emails}


# cronjob: to be run periodically to fetch pending emails, and send them
@router.post("/cronjob-send-queued-emails")
async def cronjob_send_queued_emails(request: Request, db: Session = Depends(get_db), authorization: str = Depends(validate_token)):
    """Cronjob endpoint to send all queued emails."""
    logger.info(f"Authorization header provided: {authorization}")
    logger.info(f"All headers: {request.headers}")
    # await send_queued_emails(db=db)
    return {"status": "Processed queued emails"}
