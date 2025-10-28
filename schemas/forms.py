"""
This module provides pydantic schemas for form submissions and related data structures.
It includes schemas for Zaansrecht form submissions, form status updates, and responses.
These schemas ensure data validation and serialization for API requests and responses.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enums import FormStatus

class ZaansrechtFormCreate(BaseModel):
    full_name: str
    email: EmailStr
    terms_accepted: bool
    telephone: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    meeting_datetime: Optional[datetime] = None
    meeting_type: Optional[str] = None  # e.g., 'in_person', 'virtual'

class ZaansrechtFormResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    status: FormStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    terms_accepted: bool
    telephone: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    meeting_datetime: Optional[datetime] = None
    meeting_type: Optional[str] = None

    class Config:
        from_attributes = True

class FormStatusUpdate(BaseModel):
    new_status: FormStatus


class FormListResponse(BaseModel):
    forms: list[ZaansrechtFormResponse]

