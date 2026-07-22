import os
import re
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    resend_api_key: str
    email_from: str
    email_to: str
    recaptcha_secret_key: str
    api_token: str | None
    recaptcha_verify_url: str = "https://www.google.com/recaptcha/api/siteverify"


@dataclass(frozen=True)
class EmailProfile:
    application: str
    resend_api_key: str
    email_from: str
    email_to: str


def get_email_profile(application: str) -> EmailProfile:
    """Resolve a trusted email profile from an application identifier."""
    normalized = application.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", normalized):
        raise ValueError("Invalid email application identifier")

    suffix = "" if normalized == "general" else f"_{normalized.upper()}"
    variable_names = {
        "resend_api_key": f"RESEND_API_KEY{suffix}",
        "email_from": f"EMAIL_FROM{suffix}",
        "email_to": f"EMAIL_TO{suffix}",
    }
    values = {field: os.getenv(name, "") for field, name in variable_names.items()}
    missing = [name for field, name in variable_names.items() if not values[field]]
    if missing:
        raise ValueError(f"Missing email configuration for '{normalized}': {', '.join(missing)}")

    return EmailProfile(application=normalized, **values)


@lru_cache
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")

    return Settings(
        database_url=database_url,
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        email_from=os.getenv("EMAIL_FROM", ""),
        email_to=os.getenv("EMAIL_TO", ""),
        recaptcha_secret_key=os.getenv("RECAPTCHA_SECRET_KEY", ""),
        api_token=os.getenv("API_TOKEN"),
    )
