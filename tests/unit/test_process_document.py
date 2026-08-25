from datetime import UTC, datetime
from pathlib import Path

import pytest

from cka.application.process_document import ProcessDocument, UnsupportedDocumentTypeError
from cka.domain.chunk import DocumentChunk
from cka.domain.chunk_repository import ChunkRepository
from cka.domain.document import Document
from cka.infrastructure.embeddings.fake_embedding_service import FakeEmbeddingService
from cka.infrastructure.processing.chunker import TextChunker
from cka.infrastructure.processing.pdf_loader import PdfDocumentLoader
from cka.infrastructure.processing.text_loader import PlainTextLoader

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "samples"


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self.saved: list[DocumentChunk] = []

    def save_many(self, chunks: list[DocumentChunk]) -> None:
        self.saved.extend(chunks)

    def get_by_document_id(self, document_id: str) -> list[DocumentChunk]:
        return [c for c in self.saved if c.document_id == document_id]

    def count(self) -> int:
        return len(self.saved)

    def delete_by_document_id(self, document_id: str) -> None:
        self.saved = [c for c in self.saved if c.document_id != document_id]


def make_document(**overrides: object) -> Document:
    defaults: dict[str, object] = {
        "id": "doc-1",
        "source_id": "SRC-SAMPLE-001",
        "filename": "remote-work-policy.txt",
        "content_type": "text/plain",
        "sha256": "a" * 64,
        "ingested_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


def build_process_document(chunk_repository: ChunkRepository) -> ProcessDocument:
    return ProcessDocument(
        loaders=[PlainTextLoader(), PdfDocumentLoader()],
        chunker=TextChunker(chunk_size=1200, overlap=200),
        embedding_service=FakeEmbeddingService(),
        chunk_repository=chunk_repository,
    )


def test_process_document_chunks_embeds_and_persists_text_document() -> None:
    repo = InMemoryChunkRepository()
    process = build_process_document(repo)
    document = make_document()

    chunks = process(document, SAMPLES_DIR / "remote-work-policy.txt")

    assert len(chunks) >= 1
    assert repo.count() == len(chunks)
    for chunk in chunks:
        assert chunk.document_id == "doc-1"
        assert chunk.source_id == "SRC-SAMPLE-001"
        assert chunk.page_number is None
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 384


def test_process_document_preserves_pdf_page_numbers() -> None:
    repo = InMemoryChunkRepository()
    process = build_process_document(repo)
    document = make_document(
        filename="expense-reimbursement-policy.pdf", content_type="application/pdf"
    )

    chunks = process(document, SAMPLES_DIR / "expense-reimbursement-policy.pdf")

    page_numbers = {chunk.page_number for chunk in chunks}
    assert page_numbers == {1, 2}


def test_process_document_chunk_indexes_are_sequential() -> None:
    repo = InMemoryChunkRepository()
    process = build_process_document(repo)
    document = make_document()

    chunks = process(document, SAMPLES_DIR / "remote-work-policy.txt")

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_process_document_raises_for_unsupported_file_type() -> None:
    repo = InMemoryChunkRepository()
    process = build_process_document(repo)
    document = make_document(filename="unknown.docx", content_type="application/msword")

    with pytest.raises(UnsupportedDocumentTypeError):
        process(document, SAMPLES_DIR / "remote-work-policy.txt")
