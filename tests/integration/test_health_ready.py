from fastapi.testclient import TestClient

from cka.main import app


def test_health_ready_returns_200_when_database_is_reachable() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
