from sqlalchemy import select
from sqlalchemy.orm import Session

from cka.domain.retrieval import RetrievalQuery, RetrievalResult, Retriever
from cka.infrastructure.database.models import ChunkModel
from cka.infrastructure.embeddings.embedding_service import EmbeddingService


class PgVectorRetriever(Retriever):
    """Vector-only retrieval via pgvector cosine distance (score = 1 - distance)."""

    def __init__(self, session: Session, embedding_service: EmbeddingService) -> None:
        self._session = session
        self._embedding_service = embedding_service

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        query_embedding = self._embedding_service.embed_one(query.text)
        distance = ChunkModel.embedding.cosine_distance(query_embedding)

        stmt = select(ChunkModel, distance.label("distance"))
        if query.access_scope is not None:
            stmt = stmt.where(ChunkModel.source_id.in_(query.access_scope.allowed_source_ids))
        stmt = stmt.order_by(distance).limit(query.top_k)

        rows = self._session.execute(stmt).all()
        return [
            RetrievalResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                source_id=chunk.source_id,
                content=chunk.content,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=1.0 - distance_value,
            )
            for chunk, distance_value in rows
        ]
