from fastapi.testclient import TestClient

from src.api.v1 import API_PREFIX, API_VERSION
from src.main import app


def test_root() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello R2D2 services"}


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_v1_api_routes_keep_their_versioned_prefix() -> None:
    """Protect existing clients from accidental route-prefix changes."""
    paths = set(app.openapi()["paths"])
    assert API_VERSION == "1"
    assert API_PREFIX == "/api/v1"
    assert "/api/v1/spanglish/quiz-options" in paths
    assert "/api/v1/spanglish/quizzes" in paths
    assert "/api/v1/email/send-email" in paths
    assert "/api/v1/forms/zaansrecht" in paths


def test_application_routes_are_not_exposed_without_a_version() -> None:
    """Require all business endpoints to opt into a public API version."""
    paths = set(app.openapi()["paths"])
    assert "/spanglish/quizzes" not in paths
    assert "/email/send-email" not in paths
    assert "/forms/zaansrecht" not in paths
