"""
This module contains the auth dependencies like the token validation.
"""

import os
import logging
from fastapi import HTTPException, status, Header
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("API_TOKEN")

logger = logging.getLogger(__name__)


def validate_token(authorization: str = Header(None)):
    """Validate the provided API token."""
    logger.info(f"Validating API token for authorization header {authorization}")
    if authorization != f"Bearer {TOKEN}":
        # logger.warning(f"Invalid API token provided: {authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True
