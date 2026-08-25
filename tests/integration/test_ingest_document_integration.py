from pathlib import Path

from sqlalchemy.orm import Session

from cka.application.ingest_document import IngestDocument
from cka.application.validate_source import ValidateSource
from cka.infrastructure.database.document_repository import SqlAlchemyDocumentRepository
from cka.infrastructure.sources.yaml_source_repository import YamlSourceRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "data" / "sources" / "registry.yaml"
SAMPLE_PATH = REPO_ROOT / "data" / "raw" / "samples" / "remote-work-policy.txt"


def build_ingest_document(db_session: Session) -> IngestDocument:
    source_repository = YamlSourceRepository(REGISTRY_PATH)
    validate_source = ValidateSource(source_repository)
    document_repository = SqlAlchemyDocumentRepository(db_session)
    return IngestDocument(validate_source, document_repository)


def test_ingest_real_sample_document_end_to_end(db_session: Session) -> None:
    ingest = build_ingest_document(db_session)
    content = SAMPLE_PATH.read_bytes()

    document = ingest(
        source_id="SRC-SAMPLE-001",
        filename=SAMPLE_PATH.name,
        content_type="text/plain",
        content=content,
    )
    db_session.commit()

    repository = SqlAlchemyDocumentRepository(db_session)
    persisted = repository.get_by_id(document.id)

    assert persisted is not None
    assert persisted.source_id == "SRC-SAMPLE-001"
    assert persisted.filename == "remote-work-policy.txt"
    assert len(persisted.sha256) == 64


def test_ingesting_identical_content_twice_is_idempotent_against_real_unique_index(
    db_session: Session,
) -> None:
    """sha256 has a real UNIQUE index (see the Alembic migration). Ingesting the
    same bytes twice must not violate that constraint — IngestDocument detects
    the existing row via get_by_sha256 and short-circuits instead of re-saving.
    """
    ingest = build_ingest_document(db_session)
    content = SAMPLE_PATH.read_bytes()

    first = ingest(
        source_id="SRC-SAMPLE-001",
        filename=SAMPLE_PATH.name,
        content_type="text/plain",
        content=content,
    )
    db_session.commit()

    second = ingest(
        source_id="SRC-SAMPLE-001",
        filename=SAMPLE_PATH.name,
        content_type="text/plain",
        content=content,
    )
    db_session.commit()

    assert first.id == second.id
