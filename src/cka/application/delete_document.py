import structlog

from cka.domain.chunk_repository import ChunkRepository
from cka.domain.document_repository import DocumentRepository
from cka.domain.exceptions import DomainError

logger = structlog.get_logger(__name__)


class DocumentNotFoundError(DomainError):
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class DeleteDocument:
    """Deletes a document and its chunks together — chunks first, to satisfy
    the document_chunks -> documents foreign key.
    """

    def __init__(
        self, document_repository: DocumentRepository, chunk_repository: ChunkRepository
    ) -> None:
        self._document_repository = document_repository
        self._chunk_repository = chunk_repository

    def __call__(self, document_id: str) -> None:
        document = self._document_repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        self._chunk_repository.delete_by_document_id(document_id)
        self._document_repository.delete(document_id)

        logger.info("document_deleted", document_id=document_id)
