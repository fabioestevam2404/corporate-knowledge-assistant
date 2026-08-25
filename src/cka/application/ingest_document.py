import uuid
from datetime import UTC, datetime

import structlog

from cka.application.document_integrity import calculate_sha256
from cka.application.validate_source import ValidateSource
from cka.domain.document import Document
from cka.domain.document_repository import DocumentRepository

logger = structlog.get_logger(__name__)


class IngestDocument:
    """Ingests one document: validates its source is governed/approved (ADR-001),
    computes a content-integrity hash, and persists it.

    Deliberately never logs raw document content — only identifiers, sizes and hashes.
    """

    def __init__(
        self,
        validate_source: ValidateSource,
        document_repository: DocumentRepository,
    ) -> None:
        self._validate_source = validate_source
        self._document_repository = document_repository

    def __call__(
        self,
        source_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> Document:
        logger.info("document_ingestion_started", source_id=source_id, filename=filename)

        self._validate_source(source_id)

        sha256 = calculate_sha256(content)
        logger.info("document_integrity_calculated", sha256=sha256, size_bytes=len(content))

        existing = self._document_repository.get_by_sha256(sha256)
        if existing is not None:
            logger.info("document_ingestion_skipped_duplicate", document_id=existing.id)
            return existing

        document = Document(
            id=str(uuid.uuid4()),
            source_id=source_id,
            filename=filename,
            content_type=content_type,
            sha256=sha256,
            ingested_at=datetime.now(UTC),
        )
        self._document_repository.save(document)

        logger.info("document_ingestion_completed", document_id=document.id)
        return document
