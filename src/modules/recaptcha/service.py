import logging

import httpx
from fastapi import Header, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_502_BAD_GATEWAY

from src.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class RecaptchaVerifier:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self.client = client

    async def verify(self, token: str) -> bool:
        if not self.settings.recaptcha_secret_key:
            raise RuntimeError("RECAPTCHA_SECRET_KEY environment variable is not set")

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=5.0)
        try:
            response = await client.post(
                self.settings.recaptcha_verify_url,
                data={"secret": self.settings.recaptcha_secret_key, "response": token},
            )
            response.raise_for_status()
            return bool(response.json().get("success"))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("reCAPTCHA verification service failed: %s", exc)
            raise HTTPException(
                status_code=HTTP_502_BAD_GATEWAY,
                detail="Captcha verification service unavailable",
            ) from exc
        finally:
            if owns_client:
                await client.aclose()


async def verify_captcha_token(authorization: str = Header(...)) -> str:
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Invalid authorization header format",
        )

    if not await RecaptchaVerifier().verify(token):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Captcha verification failed")
    return token
