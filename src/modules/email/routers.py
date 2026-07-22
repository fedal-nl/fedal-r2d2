from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.dependencies.auth import validate_token
from src.enums import EmailStatus
from src.modules.email.schemas import EmailSendRequest
from src.modules.email.service import EmailMessage, EmailService

router = APIRouter()


@router.post("/send-email")
def send_email_route(
    request: EmailSendRequest,
    db: Session = Depends(get_db),
    authorization: bool = Depends(validate_token),
):
    try:
        log = EmailService(db).send(EmailMessage(**request.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": log.id, "status": log.status}


@router.get("/sent-emails")
def get_sent_emails(db: Session = Depends(get_db), status: EmailStatus = EmailStatus.SENT):
    return EmailService(db).get_by_status(status)


@router.get("/email-status/{email_id}")
def get_email_status(email_id: int, db: Session = Depends(get_db)):
    status = EmailService(db).get_status(email_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Email not found")
    return {"email_id": email_id, "status": status}


@router.get("/all-emails")
def get_all_emails(db: Session = Depends(get_db)):
    return {"all_emails": EmailService(db).get_all()}
