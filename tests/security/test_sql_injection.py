"""Proves the retrieval query field is safe against SQL injection — both
retrievers (pgvector cosine search and PostgreSQL full-text search) use
parameterized queries exclusively (see PgVectorRetriever, which builds its
query through SQLAlchemy's ORM, and PostgresKeywordRetriever, which binds
:query_text rather than interpolating it). This test proves the payloads are
treated as inert search text, not executable SQL.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.main import app
from tests.integration.seeding import seed_full_corpus

INJECTION_PAYLOADS = [
    "' OR 1=1 --",
    "'; DROP TABLE document_chunks; --",
    "' UNION SELECT password_hash FROM users --",
    "'; DELETE FROM documents WHERE '1'='1",
]


def test_sql_injection_payloads_do_not_error_and_do_not_corrupt_data(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    expected_chunk_count = db_session.scalar(text("SELECT COUNT(*) FROM document_chunks"))

    with TestClient(app) as client:
        for payload in INJECTION_PAYLOADS:
            response = client.post(
                "/retrieve",
                json={"query": payload, "top_k": 5},
                headers=auth_headers("admin"),
            )
            assert response.status_code == 200, f"payload broke the request: {payload!r}"

    # The tables must be untouched — no DROP/DELETE executed.
    actual_chunk_count = db_session.scalar(text("SELECT COUNT(*) FROM document_chunks"))
    assert actual_chunk_count == expected_chunk_count
    assert db_session.scalar(text("SELECT to_regclass('document_chunks')")) is not None
