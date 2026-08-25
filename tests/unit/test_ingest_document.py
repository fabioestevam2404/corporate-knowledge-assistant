import pytest

from cka.application.ingest_document import IngestDocument
from cka.application.validate_source import ValidateSource
from cka.domain.document import Document
from cka.domain.document_repository import DocumentRepository
from cka.domain.exceptions import SourceNotApprovedError
from cka.domain.source import Source
from cka.domain.source_repository import SourceRepository


class InMemorySourceRepository(SourceRepository):
    def __init__(self, sources: list[Source]) -> None:
        self._sources = {s.id: s for s in sources}

    def get_by_id(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def list_sources(self) -> list[Source]:
        return list(self._sources.values())


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, Document] = {}
        self._by_sha256: dict[str, Document] = {}

    def save(self, document: Document) -> None:
        self._by_id[document.id] = document
        self._by_sha256[document.sha256] = document

    def get_by_id(self, document_id: str) -> Document | None:
        return self._by_id.get(document_id)

    def get_by_sha256(self, sha256: str) -> Document | None:
        return self._by_sha256.get(sha256)

    def delete(self, document_id: str) -> None:
        document = self._by_id.pop(document_id, None)
        if document is not None:
            self._by_sha256.pop(document.sha256, None)


def make_source(**overrides: object) -> Source:
    defaults: dict[str, object] = {
        "id": "SRC-001",
        "name": "Sample Source",
        "organization": "Acme",
        "source_type": "internal_policy",
        "url": "data/raw/samples/sample.txt",
        "license": "CC0-1.0",
        "access_level": "public",
        "status": "approved",
        "allowed_for_ingestion": True,
    }
    defaults.update(overrides)
    return Source(**defaults)  # type: ignore[arg-type]


def make_ingest_document(source: Source, document_repo: DocumentRepository) -> IngestDocument:
    validate_source = ValidateSource(InMemorySourceRepository([source]))
    return IngestDocument(validate_source, document_repo)


def test_ingest_document_persists_and_returns_document() -> None:
    source = make_source()
    repo = InMemoryDocumentRepository()
    ingest = make_ingest_document(source, repo)

    document = ingest(
        source_id="SRC-001",
        filename="sample.txt",
        content_type="text/plain",
        content=b"hello world",
    )

    assert document.source_id == "SRC-001"
    assert document.filename == "sample.txt"
    assert repo.get_by_id(document.id) == document


def test_ingest_document_rejects_unapproved_source() -> None:
    source = make_source(status="pending")
    repo = InMemoryDocumentRepository()
    ingest = make_ingest_document(source, repo)

    with pytest.raises(SourceNotApprovedError):
        ingest(
            source_id="SRC-001",
            filename="sample.txt",
            content_type="text/plain",
            content=b"hello world",
        )


def test_ingest_document_is_idempotent_for_identical_content() -> None:
    source = make_source()
    repo = InMemoryDocumentRepository()
    ingest = make_ingest_document(source, repo)

    first = ingest(
        source_id="SRC-001",
        filename="sample.txt",
        content_type="text/plain",
        content=b"same bytes",
    )
    second = ingest(
        source_id="SRC-001",
        filename="sample-renamed.txt",
        content_type="text/plain",
        content=b"same bytes",
    )

    assert first.id == second.id
