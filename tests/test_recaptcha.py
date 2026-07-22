import httpx
import pytest
from fastapi import HTTPException

from src.core.config import Settings
from src.modules.recaptcha.service import RecaptchaVerifier, verify_captcha_token


class FakeResponse:
    def __init__(self, payload, error: bool = False):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            request = httpx.Request("POST", "https://example.com")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("unavailable", request=request, response=response)

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.data = None

    async def post(self, url, data):
        self.data = data
        return self.response


SETTINGS = Settings(
    database_url="postgresql://test:test@localhost/test",
    resend_api_key="key",
    email_from="from@example.com",
    email_to="to@example.com",
    recaptcha_secret_key="secret",
    api_token="token",
)


@pytest.mark.asyncio
async def test_recaptcha_accepts_valid_token() -> None:
    client = FakeClient(FakeResponse({"success": True}))
    assert await RecaptchaVerifier(SETTINGS, client).verify("captcha-token") is True
    assert client.data == {"secret": "secret", "response": "captcha-token"}


@pytest.mark.asyncio
async def test_recaptcha_rejects_invalid_token() -> None:
    client = FakeClient(FakeResponse({"success": False}))
    assert await RecaptchaVerifier(SETTINGS, client).verify("bad-token") is False


@pytest.mark.asyncio
async def test_recaptcha_translates_upstream_failure() -> None:
    client = FakeClient(FakeResponse({}, error=True))
    with pytest.raises(HTTPException) as exc_info:
        await RecaptchaVerifier(SETTINGS, client).verify("token")
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_recaptcha_header_dependency(monkeypatch) -> None:
    async def valid(self, token):
        return True

    monkeypatch.setattr(RecaptchaVerifier, "verify", valid)
    assert await verify_captcha_token("Bearer captcha-token") == "captcha-token"


@pytest.mark.asyncio
@pytest.mark.parametrize("header", ["token", "Basic token", "Bearer "])
async def test_recaptcha_header_dependency_rejects_malformed_header(header) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await verify_captcha_token(header)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_recaptcha_header_dependency_rejects_invalid_token(monkeypatch) -> None:
    async def invalid(self, token):
        return False

    monkeypatch.setattr(RecaptchaVerifier, "verify", invalid)
    with pytest.raises(HTTPException) as exc_info:
        await verify_captcha_token("Bearer invalid")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_recaptcha_requires_secret() -> None:
    settings = SETTINGS.__class__(**{**SETTINGS.__dict__, "recaptcha_secret_key": ""})
    with pytest.raises(RuntimeError, match="RECAPTCHA_SECRET_KEY"):
        await RecaptchaVerifier(settings, FakeClient(FakeResponse({}))).verify("token")
