import math
from typing import TYPE_CHECKING

from cka.domain.ranking import Reranker
from cka.domain.retrieval import RetrievalResult

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

DEFAULT_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _sigmoid(x: float) -> float:
    """Maps ms-marco-MiniLM-L-6-v2's raw, unbounded relevance logit (can be
    strongly negative for an irrelevant pair, and isn't capped above 1 for
    a strongly relevant one) into (0, 1) -- monotonic, so ranking order is
    unaffected, but the *absolute* value becomes comparable to
    Settings.rag_min_retrieval_score, which assumes a bounded score.
    A real defect (see docs/release-gate/PROGRESS.md, Block 4/Sprint 15):
    without this, a correctly top-ranked, genuinely relevant result could
    still fail the qualifying threshold whenever its raw logit happened to
    be negative, causing AskKnowledgeBase to abstain despite retrieval
    having found the right evidence.
    """
    return 1.0 / (1.0 + math.exp(-x))


class CrossEncoderReranker(Reranker):
    """Reranks the fused hybrid-retrieval candidate set only (never the whole
    corpus) with a cross-encoder, per ADR-007. Model import/load deferred to
    first use — same rationale as SentenceTransformerEmbeddingService.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None

    def _get_model(self) -> "CrossEncoder":
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        if not results:
            return []

        pairs = [(query_text, result.content) for result in results]
        scores = self._get_model().predict(pairs)

        reranked = [
            RetrievalResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                source_id=result.source_id,
                content=result.content,
                page_number=result.page_number,
                chunk_index=result.chunk_index,
                score=_sigmoid(float(score)),
            )
            for result, score in zip(results, scores, strict=True)
        ]
        reranked.sort(key=lambda r: r.score, reverse=True)
        return reranked
