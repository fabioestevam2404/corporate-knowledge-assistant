from fastapi.testclient import TestClient

from cka.main import app


def test_root_returns_running_status() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Corporate Knowledge Assistant API",
        "status": "running",
    }


def test_health_returns_healthy() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "corporate-knowledge-assistant",
    }


def test_health_live_returns_alive() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
