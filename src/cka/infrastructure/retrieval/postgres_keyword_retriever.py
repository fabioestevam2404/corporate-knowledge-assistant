from sqlalchemy import text
from sqlalchemy.orm import Session

from cka.domain.retrieval import RetrievalQuery, RetrievalResult, Retriever

_QUERY_SQL = text(
    """
    SELECT id, document_id, source_id, content, page_number, chunk_index,
           ts_rank(search_vector, websearch_to_tsquery('simple', :query_text)) AS rank
    FROM document_chunks
    WHERE search_vector @@ websearch_to_tsquery('simple', :query_text)
      AND (:has_scope = false OR source_id = ANY(:allowed_source_ids))
    ORDER BY rank DESC
    LIMIT :top_k
    """
)


class PostgresKeywordRetriever(Retriever):
    """Lexical retrieval via PostgreSQL Full Text Search (ADR-007) — catches
    exact terms, codes and acronyms that vector search alone can miss.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        has_scope = query.access_scope is not None
        allowed_source_ids = (
            list(query.access_scope.allowed_source_ids) if query.access_scope else []
        )

        rows = self._session.execute(
            _QUERY_SQL,
            {
                "query_text": query.text,
                "has_scope": has_scope,
                "allowed_source_ids": allowed_source_ids,
                "top_k": query.top_k,
            },
        ).all()

        return [
            RetrievalResult(
                chunk_id=row.id,
                document_id=row.document_id,
                source_id=row.source_id,
                content=row.content,
                page_number=row.page_number,
                chunk_index=row.chunk_index,
                score=float(row.rank),
            )
            for row in rows
        ]
