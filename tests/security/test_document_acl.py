"""The roadmap's flagship security proof point (Release Gate §7):

    Documento A (PUBLIC) e Documento B (MANAGEMENT). Usuário com role
    EMPLOYEE pergunta: 'Qual é o conteúdo do Documento B?' O retrieval não
    deve retornar o Documento B.

SRC-SAMPLE-003 (Executive Compensation Framework) is registered with
access_level: management. An EMPLOYEE-role user must never see it in
retrieval results, and /ask must abstain rather than answer from it — for
real, against the real corpus, real embeddings, real hybrid retrieval, real
reranking, and a real per-role AccessScope (not a mock).
"""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.main import app
from tests.integration.seeding import seed_full_corpus


def test_employee_retrieval_never_returns_the_management_document(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/retrieve",
            json={
                "query": "What is the executive compensation framework and its scope?",
                "top_k": 10,
            },
            headers=auth_headers("employee"),
        )

    assert response.status_code == 200
    source_ids = {r["source_id"] for r in response.json()["results"]}
    assert "SRC-SAMPLE-003" not in source_ids


def test_employee_ask_about_management_document_abstains(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={"query": "What is the executive compensation framework and its scope?"},
            headers=auth_headers("employee"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["sources"] == []
    assert not any(s.get("document_id") for s in body["sources"])


def test_manager_retrieval_can_see_the_management_document(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    # Positive control: proves the exclusion above is real authorization, not
    # a bug that hides the document from everyone.
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/retrieve",
            json={
                "query": "What is the executive compensation framework and its scope?",
                "top_k": 10,
            },
            headers=auth_headers("manager"),
        )

    source_ids = {r["source_id"] for r in response.json()["results"]}
    assert "SRC-SAMPLE-003" in source_ids


def test_admin_retrieval_can_see_the_management_document(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    seed_full_corpus(db_session, real_embedding_service)

    with TestClient(app) as client:
        response = client.post(
            "/retrieve",
            json={
                "query": "What is the executive compensation framework and its scope?",
                "top_k": 10,
            },
            headers=auth_headers("admin"),
        )

    source_ids = {r["source_id"] for r in response.json()["results"]}
    assert "SRC-SAMPLE-003" in source_ids
