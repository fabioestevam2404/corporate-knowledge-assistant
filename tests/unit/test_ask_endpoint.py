from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cka.api.dependencies import get_access_scope, get_ask_knowledge_base, get_current_user
from cka.domain.evidence import GroundedAnswer, SourceReference
from cka.domain.retrieval import AccessScope
from cka.infrastructure.security.jwt import TokenPayload
from cka.main import app


class StubAskKnowledgeBase:
    def __init__(self, answer: GroundedAnswer) -> None:
        self._answer = answer
        self.calls: list[tuple[str, AccessScope, str]] = []

    def __call__(self, query_text: str, access_scope: AccessScope, trace_id: str) -> GroundedAnswer:
        self.calls.append((query_text, access_scope, trace_id))
        return self._answer


@pytest.fixture
def client() -> Iterator[TestClient]:
    # get_current_user is overridden because /ask's rate-limit dependency
    # depends on it directly (not just via get_access_scope) — without this,
    # these tests would 401 on a missing bearer token.
    app.dependency_overrides[get_current_user] = lambda: TokenPayload(user_id="u1", role="employee")
    app.dependency_overrides[get_access_scope] = lambda: AccessScope(
        user_id="u1", role="employee", allowed_source_ids=frozenset({"SRC-1"})
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_access_scope, None)
    app.dependency_overrides.pop(get_ask_knowledge_base, None)


def test_ask_endpoint_returns_grounded_answer(client: TestClient) -> None:
    stub = StubAskKnowledgeBase(
        GroundedAnswer(
            answer="You may work remotely 3 days a week.",
            sources=[
                SourceReference(
                    source_id="SRC-1", document_id="doc-1", page_number=2, chunk_id="c1"
                )
            ],
            confidence="high",
            grounded=True,
        )
    )
    app.dependency_overrides[get_ask_knowledge_base] = lambda: stub

    response = client.post("/ask", json={"query": "How many remote days?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "You may work remotely 3 days a week."
    assert body["grounded"] is True
    assert body["confidence"] == "high"
    assert body["sources"] == [{"document_id": "doc-1", "page_number": 2, "chunk_id": "c1"}]
    assert "trace_id" in body and body["trace_id"]
    assert stub.calls[0][0] == "How many remote days?"


def test_ask_endpoint_returns_abstention_response(client: TestClient) -> None:
    stub = StubAskKnowledgeBase(
        GroundedAnswer(
            answer="Não encontrei evidências suficientes para responder.",
            sources=[],
            confidence="low",
            grounded=False,
        )
    )
    app.dependency_overrides[get_ask_knowledge_base] = lambda: stub

    response = client.post("/ask", json={"query": "What was 2025 profit?"})

    body = response.json()
    assert body["grounded"] is False
    assert body["sources"] == []


def test_ask_endpoint_rejects_query_over_max_length(client: TestClient) -> None:
    app.dependency_overrides[get_ask_knowledge_base] = lambda: StubAskKnowledgeBase(
        GroundedAnswer(answer="unused", sources=[], confidence="low", grounded=False)
    )

    response = client.post("/ask", json={"query": "x" * 2001})

    assert response.status_code == 400


def test_ask_endpoint_rejects_empty_query(client: TestClient) -> None:
    response = client.post("/ask", json={"query": ""})

    assert response.status_code == 422


def test_ask_endpoint_requires_authentication() -> None:
    # Deliberately no dependency overrides and no Authorization header.
    with TestClient(app) as unauthenticated_client:
        response = unauthenticated_client.post("/ask", json={"query": "anything"})

    assert response.status_code == 401
