import uuid
from pathlib import Path

import structlog

from cka.domain.chunk import DocumentChunk
from cka.domain.chunk_repository import ChunkRepository
from cka.domain.document import Document
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.processing.chunker import TextChunker
from cka.infrastructure.processing.loader import DocumentLoader
from cka.infrastructure.processing.normalizer import normalize_text

logger = structlog.get_logger(__name__)


class UnsupportedDocumentTypeError(Exception):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"No loader supports file: {filename}")


class ProcessDocument:
    """Chunks and embeds an already-ingested Document (see IngestDocument), and
    persists the resulting chunks. Runs after ingestion, on the same
    source-governed content — never on unvalidated input.
    """

    def __init__(
        self,
        loaders: list[DocumentLoader],
        chunker: TextChunker,
        embedding_service: EmbeddingService,
        chunk_repository: ChunkRepository,
    ) -> None:
        self._loaders = loaders
        self._chunker = chunker
        self._embedding_service = embedding_service
        self._chunk_repository = chunk_repository

    def __call__(self, document: Document, file_path: Path) -> list[DocumentChunk]:
        logger.info("document_processing_started", document_id=document.id)

        loader = self._select_loader(document.filename)
        pages = loader.load(file_path)

        pending: list[tuple[str, int | None, int]] = []
        for page in pages:
            normalized = normalize_text(page.text)
            for chunked in self._chunker.chunk(normalized):
                pending.append((chunked.content, page.page_number, chunked.token_count))

        embeddings = (
            self._embedding_service.embed([content for content, _, _ in pending]) if pending else []
        )

        chunks = [
            DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                source_id=document.source_id,
                chunk_index=index,
                content=content,
                page_number=page_number,
                token_count=token_count,
                embedding=embedding,
            )
            for index, ((content, page_number, token_count), embedding) in enumerate(
                zip(pending, embeddings, strict=True)
            )
        ]

        self._chunk_repository.save_many(chunks)

        logger.info(
            "document_processing_completed",
            document_id=document.id,
            chunk_count=len(chunks),
        )
        return chunks

    def _select_loader(self, filename: str) -> DocumentLoader:
        for loader in self._loaders:
            if loader.supports(filename):
                return loader
        raise UnsupportedDocumentTypeError(filename)
