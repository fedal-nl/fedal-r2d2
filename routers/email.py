# app/routers/email.py
import logging
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from configs.db import get_db
from services.emai_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/send-email")
async def send_email_route(
    background_tasks: BackgroundTasks,
    sender: str,
    subject: str,
    message: str,
    db: Session = Depends(get_db)
):
    email_service = EmailService(db)

    background_tasks.add_task(
        email_service.send_email, sender, subject, message
    )

    logger.info("Email sending initiated for %s", sender)

    return {"status": "Email queued for sending"}

@router.get("/sent-emails")
async def get_sent_emails(db: Session = Depends(get_db)):
    email_service = EmailService(db)
    sent_emails = email_service.get_sent_emails()
    return {"sent_emails": sent_emails}

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
