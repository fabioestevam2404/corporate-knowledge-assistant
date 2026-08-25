from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cka.api.dependencies import (
    get_current_user,
    get_delete_document,
    get_ingest_document,
    get_process_document,
)
from cka.domain.document import Document
from cka.infrastructure.security.jwt import TokenPayload
from cka.main import app


def as_role(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: TokenPayload(user_id="u1", role=role)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_ingest_document, None)
    app.dependency_overrides.pop(get_process_document, None)
    app.dependency_overrides.pop(get_delete_document, None)


def test_employee_cannot_upload_documents(client: TestClient) -> None:
    as_role("employee")

    response = client.post(
        "/documents",
        data={"source_id": "SRC-SAMPLE-001"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 403


def test_manager_cannot_upload_documents(client: TestClient) -> None:
    as_role("manager")

    response = client.post(
        "/documents",
        data={"source_id": "SRC-SAMPLE-001"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 403


def test_employee_cannot_delete_documents(client: TestClient) -> None:
    as_role("employee")

    response = client.delete("/documents/some-id")

    assert response.status_code == 403


def test_unauthenticated_request_is_rejected_before_rbac(client: TestClient) -> None:
    response = client.post(
        "/documents",
        data={"source_id": "SRC-SAMPLE-001"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 401


def test_admin_can_upload_documents(client: TestClient) -> None:
    as_role("admin")
    document = Document(
        id="doc-1",
        source_id="SRC-SAMPLE-001",
        filename="test.txt",
        content_type="text/plain",
        sha256="a" * 64,
        ingested_at=datetime.now(UTC),
    )
    app.dependency_overrides[get_ingest_document] = lambda: lambda **kwargs: document
    app.dependency_overrides[get_process_document] = lambda: (
        lambda doc, path: [] if isinstance(path, Path) else []
    )

    response = client.post(
        "/documents",
        data={"source_id": "SRC-SAMPLE-001"},
        files={"file": ("test.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["document_id"] == "doc-1"
