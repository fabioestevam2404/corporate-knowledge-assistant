from sqlalchemy.orm import Session

from cka.domain.document import Document
from cka.domain.document_repository import DocumentRepository
from cka.infrastructure.database.models import DocumentModel


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, document: Document) -> None:
        model = DocumentModel(
            id=document.id,
            source_id=document.source_id,
            filename=document.filename,
            content_type=document.content_type,
            sha256=document.sha256,
            ingested_at=document.ingested_at,
        )
        self._session.merge(model)
        # Flushed (not just merged) so the row is visible to any subsequent
        # insert in the same session/transaction that FK-references it — e.g.
        # ProcessDocument saving chunks right after IngestDocument saves the
        # document, as the real POST /documents endpoint does. DocumentModel
        # and ChunkModel have no ORM relationship() between them, so
        # SQLAlchemy's flush can't infer document-before-chunk insert order
        # on its own (a real bug this exact gap caused — see Block 2/3
        # PROGRESS.md).
        self._session.flush()

    def get_by_id(self, document_id: str) -> Document | None:
        model = self._session.get(DocumentModel, document_id)
        return self._to_domain(model) if model else None

    def get_by_sha256(self, sha256: str) -> Document | None:
        model = (
            self._session.query(DocumentModel).filter(DocumentModel.sha256 == sha256).one_or_none()
        )
        return self._to_domain(model) if model else None

    def delete(self, document_id: str) -> None:
        model = self._session.get(DocumentModel, document_id)
        if model is not None:
            self._session.delete(model)

    @staticmethod
    def _to_domain(model: DocumentModel) -> Document:
        return Document(
            id=model.id,
            source_id=model.source_id,
            filename=model.filename,
            content_type=model.content_type,
            sha256=model.sha256,
            ingested_at=model.ingested_at,
        )
