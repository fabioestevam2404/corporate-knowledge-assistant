import structlog

from cka.domain.retrieval import RetrievalQuery, RetrievalResult, Retriever
from cka.infrastructure.retrieval.rrf import reciprocal_rank_fusion

logger = structlog.get_logger(__name__)


class HybridRetriever(Retriever):
    """Vector + keyword retrieval fused by Reciprocal Rank Fusion (ADR-007).

    Resilience: if the keyword retriever fails, falls back to vector-only
    results rather than failing the whole request — logged explicitly, never
    a silent degrade.
    """

    def __init__(
        self,
        vector_retriever: Retriever,
        keyword_retriever: Retriever,
        candidate_k: int,
        rrf_k: int,
    ) -> None:
        self._vector_retriever = vector_retriever
        self._keyword_retriever = keyword_retriever
        self._candidate_k = candidate_k
        self._rrf_k = rrf_k

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        candidate_query = RetrievalQuery(
            text=query.text,
            top_k=max(query.top_k, min(self._candidate_k, 20)),
            access_scope=query.access_scope,
        )

        vector_results = self._vector_retriever.retrieve(candidate_query)

        try:
            keyword_results = self._keyword_retriever.retrieve(candidate_query)
        except Exception as exc:
            logger.warning("keyword_retrieval_unavailable", error=str(exc))
            keyword_results = []

        fused = reciprocal_rank_fusion([vector_results, keyword_results], k=self._rrf_k)
        return fused[: query.top_k]
