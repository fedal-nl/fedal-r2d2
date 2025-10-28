"""
This module provides the routes for form handling, including creating new form submissions, retrieving forms by status, and updating form statuses.
It leverages the FormService for business logic and database interactions.
"""

from fastapi import APIRouter, Depends, HTTPException
from schemas.forms import ZaansrechtFormCreate, ZaansrechtFormResponse, FormStatusUpdate, FormListResponse
from sqlalchemy.orm import Session
from configs.db import get_db
from services.form_service import FormService
from enums import FormStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/zaansrecht", response_model=ZaansrechtFormResponse)
def create_zaansrecht_form(form: ZaansrechtFormCreate, db: Session = Depends(get_db)):
    """Create a new Zaansrecht form submission."""
    form_service = FormService(db)
    created_form = form_service.create_zaansrecht_form(**form.model_dump())
    return created_form


@router.get("/", response_model=FormListResponse)
def get_forms(status: FormStatus = None, db: Session = Depends(get_db)):
    """Retrieve all forms with a specific status or all forms if no status is provided."""
    form_service = FormService(db)
    forms = form_service.get_forms_by_status_or_all(status)
    # convert to response model
    forms = [ZaansrechtFormResponse.from_orm(form) for form in forms]
    return FormListResponse(forms=forms)

@router.put("/{form_id}/status", response_model=ZaansrechtFormResponse)
def update_form_status(form_id: int, status_update: FormStatusUpdate, db: Session = Depends(get_db)):
    """Update the status of a specific form."""
    form_service = FormService(db)
    updated_form = form_service.update_form_status(form_id, status_update.new_status)
    if not updated_form:
        raise HTTPException(status_code=404, detail="Form not found")
    return updated_form
