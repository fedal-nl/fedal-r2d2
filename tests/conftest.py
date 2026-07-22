import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("RESEND_API_KEY", "re_test")
os.environ.setdefault("EMAIL_FROM", "R2D2 <noreply@example.com>")
os.environ.setdefault("EMAIL_TO", "owner@example.com")
os.environ.setdefault("RESEND_API_KEY_ZAANSRECHT", "re_zaansrecht_test")
os.environ.setdefault("EMAIL_FROM_ZAANSRECHT", "Zaansrecht <noreply@zaansrecht.example>")
os.environ.setdefault("EMAIL_TO_ZAANSRECHT", "owner@zaansrecht.example")
os.environ.setdefault("RECAPTCHA_SECRET_KEY", "recaptcha-test-secret")
os.environ.setdefault("API_TOKEN", "api-test-token")
