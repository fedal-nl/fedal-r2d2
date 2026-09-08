"""Compose every route that belongs to the stable version 1 API."""

from fastapi import APIRouter

from src.auth import routers as auth
from src.apps.spanglish import routers as spanglish
from src.modules.email import routers as email
from src.modules.forms import routers as form

API_VERSION = "1"
API_PREFIX = f"/api/v{API_VERSION}"

router = APIRouter(prefix=API_PREFIX)
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(email.router, prefix="/email", tags=["Email"])
router.include_router(form.router, prefix="/forms", tags=["Forms"])
router.include_router(spanglish.router, prefix="/spanglish", tags=["Spanglish"])
