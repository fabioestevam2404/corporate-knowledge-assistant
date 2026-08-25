from cka.domain.retrieval import RetrievalQuery, RetrievalResult, Retriever
from cka.infrastructure.retrieval.hybrid_retriever import HybridRetriever


def make_result(chunk_id: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="SRC-1",
        content=f"content {chunk_id}",
        page_number=None,
        chunk_index=0,
        score=0.0,
    )


class FakeRetriever(Retriever):
    def __init__(self, results: list[RetrievalResult] | None = None, fail: bool = False) -> None:
        self._results = results or []
        self._fail = fail

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        if self._fail:
            raise RuntimeError("keyword search exploded")
        return self._results


def test_hybrid_retriever_fuses_vector_and_keyword_results() -> None:
    vector = FakeRetriever([make_result("a"), make_result("b")])
    keyword = FakeRetriever([make_result("b"), make_result("c")])
    hybrid = HybridRetriever(vector, keyword, candidate_k=20, rrf_k=60)

    results = hybrid.retrieve(RetrievalQuery(text="q", top_k=5))

    assert {r.chunk_id for r in results} == {"a", "b", "c"}


def test_hybrid_retriever_falls_back_to_vector_only_when_keyword_fails() -> None:
    vector = FakeRetriever([make_result("a"), make_result("b")])
    keyword = FakeRetriever(fail=True)
    hybrid = HybridRetriever(vector, keyword, candidate_k=20, rrf_k=60)

    results = hybrid.retrieve(RetrievalQuery(text="q", top_k=5))

    assert {r.chunk_id for r in results} == {"a", "b"}


def test_hybrid_retriever_respects_top_k() -> None:
    vector = FakeRetriever([make_result("a"), make_result("b"), make_result("c")])
    keyword = FakeRetriever([])
    hybrid = HybridRetriever(vector, keyword, candidate_k=20, rrf_k=60)

    results = hybrid.retrieve(RetrievalQuery(text="q", top_k=2))

    assert len(results) == 2
