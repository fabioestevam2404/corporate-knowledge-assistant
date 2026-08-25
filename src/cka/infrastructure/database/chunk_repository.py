from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from cka.domain.chunk import DocumentChunk
from cka.domain.chunk_repository import ChunkRepository
from cka.infrastructure.database.models import ChunkModel


class SqlAlchemyChunkRepository(ChunkRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_many(self, chunks: list[DocumentChunk]) -> None:
        for chunk in chunks:
            model = ChunkModel(
                id=chunk.id,
                document_id=chunk.document_id,
                source_id=chunk.source_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                token_count=chunk.token_count,
                embedding=chunk.embedding,
            )
            self._session.merge(model)

    def get_by_document_id(self, document_id: str) -> list[DocumentChunk]:
        stmt = (
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.chunk_index)
        )
        models = self._session.scalars(stmt).all()
        return [self._to_domain(model) for model in models]

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(ChunkModel)) or 0

    def delete_by_document_id(self, document_id: str) -> None:
        self._session.execute(delete(ChunkModel).where(ChunkModel.document_id == document_id))

    @staticmethod
    def _to_domain(model: ChunkModel) -> DocumentChunk:
        return DocumentChunk(
            id=model.id,
            document_id=model.document_id,
            source_id=model.source_id,
            chunk_index=model.chunk_index,
            content=model.content,
            page_number=model.page_number,
            token_count=model.token_count,
            embedding=list(model.embedding) if model.embedding is not None else None,
        )
