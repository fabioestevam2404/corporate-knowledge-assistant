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
