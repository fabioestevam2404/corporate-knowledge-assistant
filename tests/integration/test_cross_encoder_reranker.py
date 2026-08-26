from cka.domain.retrieval import RetrievalResult
from cka.infrastructure.ranking.cross_encoder_reranker import CrossEncoderReranker


def make_result(chunk_id: str, content: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="SRC-1",
        content=content,
        page_number=None,
        chunk_index=0,
        score=0.5,
    )


def test_cross_encoder_reranker_prefers_the_semantically_closer_passage() -> None:
    reranker = CrossEncoderReranker()
    candidates = [
        make_result(
            "remote",
            "Employees may work remotely up to three days per week with manager approval.",
        ),
        make_result(
            "security",
            "Passwords must be at least twelve characters and stored only as salted hashes.",
        ),
    ]

    reranked = reranker.rerank("What are the password requirements?", candidates)

    assert reranked[0].chunk_id == "security"
    assert reranked[0].score >= reranked[1].score


def test_cross_encoder_reranker_returns_empty_for_no_candidates() -> None:
    reranker = CrossEncoderReranker()

    assert reranker.rerank("anything", []) == []


def test_cross_encoder_reranker_scores_are_bounded_between_zero_and_one() -> None:
    # Regression test for a real defect found once this ran against a real
    # query (see docs/release-gate/PROGRESS.md, Block 4/Sprint 15): the
    # model's raw logit is unbounded and often negative even for a
    # correctly top-ranked, genuinely relevant result -- AskKnowledgeBase
    # compares this score against Settings.rag_min_retrieval_score (0.50),
    # which assumes a bounded score, so an unclamped negative logit caused
    # the system to abstain despite having found the right evidence.
    reranker = CrossEncoderReranker()
    candidates = [
        make_result("relevant", "Passwords must be at least twelve characters."),
        make_result("irrelevant", "The office coffee machine is on the third floor."),
    ]

    reranked = reranker.rerank("What are the password requirements?", candidates)

    for result in reranked:
        assert 0.0 <= result.score <= 1.0
