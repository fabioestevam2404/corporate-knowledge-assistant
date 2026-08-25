from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cka.core.config import get_settings
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.main import app
from tests.integration.seeding import seed_full_corpus


def test_ask_endpoint_end_to_end_real_retrieval(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    """Exercises the real HTTP stack: auth, retrieval, ACL scope, reranking,
    context building and prompt assembly are all real. The LLM call itself
    uses whichever provider main.py's lifespan wired up (FakeLLMProvider when
    no ANTHROPIC_API_KEY is configured), so this always runs — it just can't
    assert on real generated text without a key.
    """
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={"query": "What are the password requirements?"},
            headers=auth_headers("employee"),
        )

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "confidence" in body
    assert "grounded" in body
    assert "trace_id" in body and body["trace_id"]


def test_ask_endpoint_rejects_query_over_max_length_for_real(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    settings = get_settings()
    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={"query": "x" * (settings.max_query_length + 1)},
            headers=auth_headers("employee"),
        )

    assert response.status_code == 400


def test_ask_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/ask", json={"query": "anything"})

    assert response.status_code == 401


@pytest.mark.skipif(
    not get_settings().anthropic_api_key,
    reason="ANTHROPIC_API_KEY not set in .env — real end-to-end generation test skipped",
)
def test_ask_endpoint_returns_real_grounded_answer_with_anthropic(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={"query": "How many days per week can I work remotely?"},
            headers=auth_headers("employee"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert any(s["document_id"] for s in body["sources"])
