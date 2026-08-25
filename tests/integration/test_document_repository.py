import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cka.domain.document import Document
from cka.infrastructure.database.document_repository import SqlAlchemyDocumentRepository


def make_document(**overrides: object) -> Document:
    defaults: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "source_id": "SRC-SAMPLE-001",
        "filename": "remote-work-policy.txt",
        "content_type": "text/plain",
        "sha256": uuid.uuid4().hex + uuid.uuid4().hex,  # 64 hex chars, sha256-shaped
        "ingested_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


def test_save_and_get_by_id_round_trips_through_real_postgres(db_session: Session) -> None:
    repo = SqlAlchemyDocumentRepository(db_session)
    document = make_document()

    repo.save(document)
    db_session.commit()

    fetched = repo.get_by_id(document.id)

    assert fetched is not None
    assert fetched.id == document.id
    assert fetched.sha256 == document.sha256
    assert fetched.source_id == document.source_id


def test_get_by_sha256_finds_persisted_document(db_session: Session) -> None:
    repo = SqlAlchemyDocumentRepository(db_session)
    document = make_document()

    repo.save(document)
    db_session.commit()

    fetched = repo.get_by_sha256(document.sha256)

    assert fetched is not None
    assert fetched.id == document.id


def test_get_by_id_returns_none_for_unknown_document(db_session: Session) -> None:
    repo = SqlAlchemyDocumentRepository(db_session)

    assert repo.get_by_id(str(uuid.uuid4())) is None
