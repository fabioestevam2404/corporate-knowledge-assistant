import time

import structlog

from cka.domain.ranking import Reranker
from cka.domain.retrieval import AccessScope, RetrievalQuery, RetrievalResult, Retriever
from cka.observability.metrics import (
    RAG_RERANKING_DURATION_SECONDS,
    RAG_RETRIEVAL_DURATION_SECONDS,
)
from cka.observability.tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer()


class RetrieveKnowledge:
    def __init__(self, retriever: Retriever, reranker: Reranker | None = None) -> None:
        self._retriever = retriever
        self._reranker = reranker

    def __call__(
        self, query_text: str, access_scope: AccessScope, top_k: int = 5
    ) -> list[RetrievalResult]:
        query = RetrievalQuery(text=query_text, top_k=top_k, access_scope=access_scope)

        with tracer.start_as_current_span("hybrid_retrieval") as span:
            span.set_attribute("retrieval.top_k", top_k)
            logger.info("retrieval_started", top_k=top_k)
            start = time.perf_counter()
            results = self._retriever.retrieve(query)
            RAG_RETRIEVAL_DURATION_SECONDS.observe(time.perf_counter() - start)
            span.set_attribute("retrieval.documents_count", len(results))
            logger.info("retrieval_completed", result_count=len(results))

        if self._reranker is None or not results:
            return results

        with tracer.start_as_current_span("reranking") as span:
            try:
                start = time.perf_counter()
                reranked = self._reranker.rerank(query_text, results)
                RAG_RERANKING_DURATION_SECONDS.observe(time.perf_counter() - start)
            except Exception as exc:
                logger.warning("reranker_unavailable", error=str(exc))
                span.set_attribute("reranking.unavailable", True)
                return results

            span.set_attribute("reranking.documents_count", len(reranked))
            logger.info("reranking_completed", result_count=len(reranked))
            return reranked[:top_k]
