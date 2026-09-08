"""
This module contains the auth dependencies like the token validation.
"""

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.auth.models import User
from src.auth.services import decode_access_token
from src.core.config import get_settings
from src.core.database import get_db
from src.modules.recaptcha.service import verify_captcha_token

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


def validate_token(authorization: str = Header(None)):
    """Validate the provided API token."""
    logger.info(f"Validating API token for authorization header {authorization}")
    if authorization != f"Bearer {get_settings().api_token}":
        # logger.warning(f"Invalid API token provided: {authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Resolve a locally issued access token to its active database user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, decode_access_token(credentials.credentials))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


__all__ = ["get_current_user", "validate_token", "verify_captcha_token"]
