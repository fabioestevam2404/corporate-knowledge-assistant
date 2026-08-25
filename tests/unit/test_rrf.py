from cka.domain.retrieval import RetrievalResult
from cka.infrastructure.retrieval.rrf import reciprocal_rank_fusion


def make_result(chunk_id: str, source_id: str = "SRC-1") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id=source_id,
        content=f"content for {chunk_id}",
        page_number=None,
        chunk_index=0,
        score=0.0,
    )


def test_fuses_two_lists_favoring_items_ranked_highly_in_both() -> None:
    vector_results = [make_result("a"), make_result("b"), make_result("c")]
    keyword_results = [make_result("b"), make_result("a"), make_result("d")]

    fused = reciprocal_rank_fusion([vector_results, keyword_results])

    fused_ids = [r.chunk_id for r in fused]
    assert fused_ids[0] in {"a", "b"}
    assert set(fused_ids) == {"a", "b", "c", "d"}


def test_item_present_in_only_one_list_still_included() -> None:
    vector_results = [make_result("a")]
    keyword_results: list[RetrievalResult] = []

    fused = reciprocal_rank_fusion([vector_results, keyword_results])

    assert [r.chunk_id for r in fused] == ["a"]


def test_empty_lists_produce_empty_result() -> None:
    assert reciprocal_rank_fusion([[], []]) == []


def test_fused_scores_are_sorted_descending() -> None:
    vector_results = [make_result("a"), make_result("b"), make_result("c")]
    keyword_results = [make_result("c"), make_result("b"), make_result("a")]

    fused = reciprocal_rank_fusion([vector_results, keyword_results])

    scores = [r.score for r in fused]
    assert scores == sorted(scores, reverse=True)
