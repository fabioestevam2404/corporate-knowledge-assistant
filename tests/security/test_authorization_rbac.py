from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "raw" / "samples" / "remote-work-policy.txt"


def test_employee_gets_403_uploading_a_document(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            data={"source_id": "SRC-SAMPLE-001"},
            files={"file": (SAMPLE_PATH.name, SAMPLE_PATH.read_bytes(), "text/plain")},
            headers=auth_headers("employee"),
        )

    assert response.status_code == 403


def test_manager_gets_403_uploading_a_document(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            data={"source_id": "SRC-SAMPLE-001"},
            files={"file": (SAMPLE_PATH.name, SAMPLE_PATH.read_bytes(), "text/plain")},
            headers=auth_headers("manager"),
        )

    assert response.status_code == 403


def test_admin_can_upload_a_real_document_end_to_end(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            data={"source_id": "SRC-SAMPLE-001"},
            files={"file": (SAMPLE_PATH.name, SAMPLE_PATH.read_bytes(), "text/plain")},
            headers=auth_headers("admin"),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["chunk_count"] >= 1


def test_admin_can_delete_a_document_they_just_uploaded(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    admin_headers = auth_headers("admin")
    with TestClient(app) as client:
        upload_response = client.post(
            "/documents",
            data={"source_id": "SRC-SAMPLE-001"},
            files={"file": (SAMPLE_PATH.name, SAMPLE_PATH.read_bytes(), "text/plain")},
            headers=admin_headers,
        )
        document_id = upload_response.json()["document_id"]

        delete_response = client.delete(f"/documents/{document_id}", headers=admin_headers)

    assert delete_response.status_code == 204


def test_employee_gets_403_deleting_a_document(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    with TestClient(app) as client:
        response = client.delete("/documents/some-id", headers=auth_headers("employee"))

    assert response.status_code == 403


def test_unauthenticated_upload_is_rejected_before_any_rbac_check() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents",
            data={"source_id": "SRC-SAMPLE-001"},
            files={"file": (SAMPLE_PATH.name, SAMPLE_PATH.read_bytes(), "text/plain")},
        )

    assert response.status_code == 401
