from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.main import app
from tests.integration.seeding import seed_full_corpus


def test_retrieve_endpoint_returns_relevant_real_chunk(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/retrieve",
            json={"query": "remote work eligibility", "top_k": 3},
            headers=auth_headers("employee"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "remote work eligibility"
    assert len(body["results"]) >= 1
    assert body["results"][0]["source_id"] == "SRC-SAMPLE-001"


def test_retrieve_endpoint_rejects_top_k_out_of_bounds(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/retrieve", json={"query": "anything", "top_k": 21}, headers=auth_headers("employee")
        )

    assert response.status_code == 422


def test_retrieve_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/retrieve", json={"query": "anything", "top_k": 3})

    assert response.status_code == 401
