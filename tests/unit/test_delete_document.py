from datetime import UTC, datetime

import pytest

from cka.application.delete_document import DeleteDocument, DocumentNotFoundError
from cka.domain.chunk import DocumentChunk
from cka.domain.chunk_repository import ChunkRepository
from cka.domain.document import Document
from cka.domain.document_repository import DocumentRepository


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self, documents: list[Document]) -> None:
        self._documents = {d.id: d for d in documents}
        self.deleted_ids: list[str] = []

    def save(self, document: Document) -> None:
        self._documents[document.id] = document

    def get_by_id(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def get_by_sha256(self, sha256: str) -> Document | None:
        return next((d for d in self._documents.values() if d.sha256 == sha256), None)

    def delete(self, document_id: str) -> None:
        self._documents.pop(document_id, None)
        self.deleted_ids.append(document_id)


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks
        self.deleted_for_document_ids: list[str] = []

    def save_many(self, chunks: list[DocumentChunk]) -> None:
        self._chunks.extend(chunks)

    def get_by_document_id(self, document_id: str) -> list[DocumentChunk]:
        return [c for c in self._chunks if c.document_id == document_id]

    def count(self) -> int:
        return len(self._chunks)

    def delete_by_document_id(self, document_id: str) -> None:
        self._chunks = [c for c in self._chunks if c.document_id != document_id]
        self.deleted_for_document_ids.append(document_id)


def make_document(**overrides: object) -> Document:
    defaults: dict[str, object] = {
        "id": "doc-1",
        "source_id": "SRC-1",
        "filename": "sample.txt",
        "content_type": "text/plain",
        "sha256": "a" * 64,
        "ingested_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


def test_delete_document_removes_document_and_chunks() -> None:
    document_repo = InMemoryDocumentRepository([make_document()])
    chunk_repo = InMemoryChunkRepository([])
    delete = DeleteDocument(document_repo, chunk_repo)

    delete("doc-1")

    assert document_repo.get_by_id("doc-1") is None
    assert chunk_repo.deleted_for_document_ids == ["doc-1"]


def test_delete_deletes_chunks_before_document() -> None:
    # Order matters for the real FK (document_chunks -> documents); assert
    # it here so a future refactor can't silently flip it.
    calls: list[str] = []

    class TrackingChunkRepo(InMemoryChunkRepository):
        def delete_by_document_id(self, document_id: str) -> None:
            calls.append("chunks")
            super().delete_by_document_id(document_id)

    class TrackingDocumentRepo(InMemoryDocumentRepository):
        def delete(self, document_id: str) -> None:
            calls.append("document")
            super().delete(document_id)

    document_repo = TrackingDocumentRepo([make_document()])
    chunk_repo = TrackingChunkRepo([])
    delete = DeleteDocument(document_repo, chunk_repo)

    delete("doc-1")

    assert calls == ["chunks", "document"]


def test_delete_raises_for_unknown_document() -> None:
    delete = DeleteDocument(InMemoryDocumentRepository([]), InMemoryChunkRepository([]))

    with pytest.raises(DocumentNotFoundError):
        delete("does-not-exist")
