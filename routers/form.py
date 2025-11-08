"""
This module provides the routes for form handling, including creating new form submissions, retrieving forms by status, and updating form statuses.
It leverages the FormService for business logic and database interactions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from schemas.forms import ZaansrechtFormCreate, ZaansrechtFormResponse, FormStatusUpdate, FormListResponse
from sqlalchemy.orm import Session
from configs.db import get_db
from dependencies.auth import verify_captcha_token
from services.form_service import FormService, FormSubmissionLogService
from enums import FormStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/zaansrecht", response_model=ZaansrechtFormResponse)
async def create_zaansrecht_form(
    request: Request,
    form: ZaansrechtFormCreate,
    db: Session = Depends(get_db),
    captcha_token: str = Depends(verify_captcha_token)
):
    """Create a new Zaansrecht form submission."""
    logger.info("Creating Zaansrecht captcha_token %s", captcha_token[:5])
    logger.debug("Request details ====================")
    logger.debug(f"Method: {request.method}")
    logger.debug(f"URL: {request.url}")
    logger.debug(f"Client: {request.client}")
    logger.debug(f"Referer: {request.headers.get('referer')}")
    logger.debug(f"User-Agent: {request.headers.get('user-agent')}")
    logger.debug(f"client x-forwarded-for: {request.headers.get('x-forwarded-for')}")
    logger.debug(f"client real ip: {request.headers.get('x-real-ip')}")
    logger.debug("===================================")
    try:
        # Create the form using the FormService and then log the submission details
        form_service = FormService(db)
        created_form = form_service.create_zaansrecht_form(**form.model_dump())
        logger.info("Created Zaansrecht form with ID %d", created_form.id)
        if not created_form:
            raise HTTPException(status_code=500, detail="Failed to create form")
        
        # Log submission details
        log_service = FormSubmissionLogService(
            db,
            form_id=created_form.id,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            x_forwarded_for=request.headers.get("x-forwarded-for"),
            x_real_ip=request.headers.get("x-real-ip"),
            captcha_token=captcha_token
        )
        log_service.log_form_submission()
        return created_form
    except Exception as e:
        logger.error("Error creating Zaansrecht form: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/", response_model=FormListResponse)
def get_forms(request: Request, db: Session = Depends(get_db), status: FormStatus|None = None):
    """Retrieve all forms with a specific status or all forms if no status is provided."""
    logger.info("Retrieving forms with status: %s", status)
    logger.debug("Request details ====================")
    logger.debug(f"Method: {request.method}")
    logger.debug(f"URL: {request.url}")
    logger.debug(f"Headers: {request.headers}")
    logger.debug(f"Client: {request.client}")
    logger.debug("===================================")
    form_service = FormService(db)
    forms = form_service.get_forms_by_status_or_all(status)
    # convert to response model
    forms = [ZaansrechtFormResponse.model_validate(form) for form in forms]
    return FormListResponse(forms=forms)

@router.put("/{form_id}/status", response_model=ZaansrechtFormResponse)
def update_form_status(form_id: int, status_update: FormStatusUpdate, db: Session = Depends(get_db)):
    """Update the status of a specific form."""
    form_service = FormService(db)
    updated_form = form_service.update_form_status(form_id, status_update.new_status)
    if not updated_form:
        raise HTTPException(status_code=404, detail="Form not found")
    return updated_form
