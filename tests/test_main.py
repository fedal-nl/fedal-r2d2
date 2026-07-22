from fastapi.testclient import TestClient

from src.main import app


def test_root() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello R2D2 services"}


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
