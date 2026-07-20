"""
This module defines the Pydantic schemas for user registration, login, and social authentication.
"""
from pydantic import BaseModel, EmailStr, Field, AnyUrl
from uuid import UUID
from src.enums import SocialMediaPlatformEnum
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(..., min_length=6)
    avatar_url: AnyUrl | None = None
    user_metadata: dict | None = None
    is_active: bool = True


class UserRead(BaseModel):
    """Schema for reading user information."""
    id: UUID
    username: str
    email: EmailStr | None = None
    avatar_url: AnyUrl | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    user_metadata: dict | None = None

    model_config = {
        "from_attributes": True
    }


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6)
    avatar_url: AnyUrl | None = None
    user_metadata: dict | None = None
    is_active: bool | None = None


class SocialProviderCreate(BaseModel):
    """Schema for creating a new social authentication provider."""
    platform: SocialMediaPlatformEnum
    platform_user_id: str = Field(..., min_length=1)
    user_id: UUID


class SocialProviderRead(BaseModel):
    """Schema for reading social authentication provider information."""
    id: int
    platform: SocialMediaPlatformEnum
    platform_user_id: str
    user_id: UUID
    created_at: datetime

    model_config = {
        "from_attributes": True
    }