from fastapi.testclient import TestClient

from cka.main import app


def test_metrics_endpoint_exposes_http_series_after_a_real_request() -> None:
    with TestClient(app) as client:
        client.get("/health")
        response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    assert 'path="/health"' in body


def test_metrics_endpoint_is_prometheus_text_format() -> None:
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.headers["content-type"].startswith("text/plain")
