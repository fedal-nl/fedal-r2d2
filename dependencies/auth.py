"""
This module contains the auth dependencies like the token validation.
"""

import os
import logging
from fastapi import HTTPException, status, Header
from dotenv import load_dotenv
import httpx
from starlette.status import HTTP_400_BAD_REQUEST


RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "your_secret_key_here")
TOKEN = os.getenv("API_TOKEN")

load_dotenv()
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


async def verify_captcha_token(authorization: str = Header(...)) -> str:
    """Dependency that verifies reCAPTCHA token and returns it for logging."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid authorization header format"
        )
    logger.debug(f"Verifying captcha token from authorization header {authorization}")
    # get the token from the second part of the header Bearer.
    captcha_token = authorization.split(" ")[1]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": captcha_token},
        )
    result = response.json()
    logger.info(f"Captcha verification response: {result}")

    if not result.get("success"):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed"
        )

    return captcha_token
