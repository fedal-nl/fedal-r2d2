"""
This module contains the auth dependencies like the token validation.
"""

import logging
from fastapi import HTTPException, status, Header

from src.core.config import get_settings
from src.modules.recaptcha.service import verify_captcha_token


logger = logging.getLogger(__name__)


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
__all__ = ["validate_token", "verify_captcha_token"]
