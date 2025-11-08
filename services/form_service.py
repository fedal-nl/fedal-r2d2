"""
This module provides services related to form handling. From saving form submissions to retrieving form data.
It includes functionalities for different types of forms, such as ZaansrechtForm, and manages their lifecycle and status.
Also it provides methods to query and manipulate form data stored in the database.
Besides basic CRUD operations, it uses the email service to send notifications based on form submissions.
"""
from sqlalchemy.orm import Session
from models.form import ZaansrechtForm, FormSubmissionLog
from enums import FormStatus
from services.emai_service import EmailService
import logging

logger = logging.getLogger(__name__)


class FormService:
    def __init__(self, db: Session):
        self.db = db

    def create_zaansrecht_form(
            self,
            full_name: str,
            email: str,
            terms_accepted: bool,
            telephone: str|None = None,
            description: str|None = None,
            subject: str|None = None,
            meeting_datetime: str|None = None,
            meeting_type: str|None = None
        ) -> ZaansrechtForm:
        """Create and save a new Zaansrecht form submission."""
        # before creating the instance of the form, convert the captcha token but only the first 5 and last five characters.
        # altered_captcha_token = f"{captcha_token[:5]}...{captcha_token[-5:]}"

        form = ZaansrechtForm(
            full_name=full_name,
            email=email,
            terms_accepted=terms_accepted,
            telephone=telephone,
            description=description,
            subject=subject,
            meeting_datetime=meeting_datetime,
            meeting_type=meeting_type,
            status=FormStatus.NEW,
        )
        self.db.add(form)
        self.db.commit()
        self.db.refresh(form)
        logger.info("Created Zaansrecht form with ID %d", form.id)
        return form

    def get_forms_by_status_or_all(self, status: FormStatus|None = None):
        """Retrieve all forms with a specific status or all forms if status is None."""
        logger.info("Retrieving forms with status: %s", status)
        if status is None:
            forms = self.db.query(ZaansrechtForm).all()
        else:
            forms = self.db.query(ZaansrechtForm).filter(ZaansrechtForm.status == status).all()
        logger.info("Retrieved %d forms with status %s", len(forms), status)
        return forms

    def update_form_status(self, form_id: int, new_status: FormStatus):
        """Update the status of a specific form."""
        form = self.db.query(ZaansrechtForm).filter(ZaansrechtForm.id == form_id).first()
        if form:
            form.status = new_status
            self.db.commit()
            logger.info("Updated form ID %d to status %s", form_id, new_status)
            return form
        logger.warning("Form with ID %d not found for status update", form_id)
        return None
    
    def send_form_notification(self, form: ZaansrechtForm):
        """Send a notification email upon form submission."""
        email_service = EmailService(self.db)
        subject = f"New Zaansrecht Form Submission from {form.subject}"
        default_body = f"A new Zaansrecht form has been submitted.\n\nDetails:\nName: {form.full_name}\nEmail: {form.email}\n"
        body = default_body if form.description is None else f"Description: {form.description}\n"
        
        email_service.queue_new_email_log(
            sender=str(form.email),
            subject=subject,
            message=body
        )
        logger.info("Queued notification email for form ID %d", form.id)


class FormSubmissionLogService:
    """Service to handle logging of form submissions. It is tightly coupled with form submissions to track metadata."""
    def __init__(self, db: Session, form_id: int, **kwargs):
        self.db = db
        self.form_id = form_id
        self.kwargs = kwargs

    def log_form_submission(self) -> FormSubmissionLog|None:
        """Log a form submission event."""

        x_forwarded_for = self._filter_x_forwarded_for(self.kwargs.get("x_forwarded_for"))
        captcha_token = self._shorten_captcha_token(self.kwargs.get("captcha_token"))
        

        log_entry = FormSubmissionLog(
            form_id=self.form_id,
            user_agent=self.kwargs.get("user_agent"),
            referrer=self.kwargs.get("referrer"),
            x_forwarded_for=x_forwarded_for,
            x_real_ip=self.kwargs.get("x_real_ip"),
            captcha_token=captcha_token
        )
        try:
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            logger.info("Logged submission for form ID %d with log ID %d", self.form_id, log_entry.id)
            return log_entry
        except Exception as e:
            logger.error("Failed to log submission for form ID %d: %s", self.form_id, e)
            self.db.rollback()
            return None

    def _filter_x_forwarded_for(self, x_forwarded_for: str|None) -> list[str]:
        """Convert a comma-separated X-Forwarded-For string into a list without spaces."""
        if x_forwarded_for:
            ip_list = [ip.strip() for ip in x_forwarded_for.split(",")]
            logger.debug("Parsed X-Forwarded-For: %s", ip_list)
            return ip_list
        return []
    
    def _shorten_captcha_token(self, captcha_token: str|None) -> str|None:
        """Shorten the captcha token for logging purposes."""
        if captcha_token and len(captcha_token) > 10:
            shortened = f"{captcha_token[:5]}...{captcha_token[-5:]}"
            logger.debug("Shortened captcha token for logging: %s", shortened)
            return shortened
        return captcha_token