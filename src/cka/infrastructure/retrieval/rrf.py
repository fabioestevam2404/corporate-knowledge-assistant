from cka.domain.retrieval import RetrievalResult

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievalResult]], k: int = DEFAULT_RRF_K
) -> list[RetrievalResult]:
    """Fuses multiple ranked result lists by Reciprocal Rank Fusion: score(d) =
    sum(1 / (k + rank(d))) across every list the chunk appears in, rank
    starting at 1. Fused at chunk_id granularity, per ADR-007.
    """
    scores: dict[str, float] = {}
    best_by_id: dict[str, RetrievalResult] = {}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1.0 / (k + rank)
            if result.chunk_id not in best_by_id:
                best_by_id[result.chunk_id] = result

    ranked_ids = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)

    return [
        RetrievalResult(
            chunk_id=best_by_id[chunk_id].chunk_id,
            document_id=best_by_id[chunk_id].document_id,
            source_id=best_by_id[chunk_id].source_id,
            content=best_by_id[chunk_id].content,
            page_number=best_by_id[chunk_id].page_number,
            chunk_index=best_by_id[chunk_id].chunk_index,
            score=scores[chunk_id],
        )
        for chunk_id in ranked_ids
    ]
