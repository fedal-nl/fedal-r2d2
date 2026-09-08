"""Public contracts for local authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    avatar_url: AnyUrl | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr | None
    avatar_url: AnyUrl | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    client_type: str | None = Field(default=None, max_length=30)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
