import uuid

from fastapi.testclient import TestClient

from cka.main import app


def test_request_id_is_generated_when_absent() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    uuid.UUID(request_id)  # raises if not a valid UUID


def test_request_id_is_echoed_back_when_provided() -> None:
    incoming_id = str(uuid.uuid4())

    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": incoming_id})

    assert response.headers.get("X-Request-ID") == incoming_id


def test_unhandled_exception_returns_sanitized_500() -> None:
    @app.get("/__boom")
    def boom() -> None:
        raise RuntimeError("sensitive internal detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
    assert "sensitive internal detail" not in response.text
