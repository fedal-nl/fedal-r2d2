import os

os.environ.update(
    {
        "DATABASE_URL": "postgresql://test:test@localhost/test",
        "RESEND_API_KEY": "re_test",
        "EMAIL_FROM": "R2D2 <noreply@example.com>",
        "EMAIL_TO": "owner@example.com",
        "RESEND_API_KEY_ZAANSRECHT": "re_zaansrecht_test",
        "EMAIL_FROM_ZAANSRECHT": "Zaansrecht <noreply@zaansrecht.example>",
        "EMAIL_TO_ZAANSRECHT": "owner@zaansrecht.example",
        "RESEND_API_KEY_AICENTRALHUB": "re_aicentralhub_test",
        "EMAIL_FROM_AICENTRALHUB": "AI Central Hub <noreply@aicentralhub.example>",
        "AICENTRALHUB_TOKEN": "aicentralhub-test-token",
        "RECAPTCHA_SECRET_KEY": "recaptcha-test-secret",
        "API_TOKEN": "api-test-token",
        "JWT_SECRET_KEY": "test-secret-key-that-is-long-enough",
    }
)
