from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.domain.ranking import Reranker
from cka.domain.retrieval import AccessScope, RetrievalQuery, RetrievalResult, Retriever


def make_result(chunk_id: str, score: float = 0.5) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="SRC-1",
        content=f"content {chunk_id}",
        page_number=None,
        chunk_index=0,
        score=score,
    )


class FakeRetriever(Retriever):
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        return self._results


class FakeReranker(Reranker):
    def __init__(self, reordered: list[RetrievalResult] | None = None, fail: bool = False) -> None:
        self._reordered = reordered
        self._fail = fail

    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        if self._fail:
            raise RuntimeError("reranker exploded")
        return self._reordered if self._reordered is not None else list(reversed(results))


def make_scope() -> AccessScope:
    return AccessScope(user_id="u1", role="employee", allowed_source_ids=frozenset({"SRC-1"}))


def test_retrieve_knowledge_without_reranker_returns_retriever_order() -> None:
    results = [make_result("a"), make_result("b")]
    use_case = RetrieveKnowledge(FakeRetriever(results))

    output = use_case("query", make_scope(), top_k=5)

    assert [r.chunk_id for r in output] == ["a", "b"]


def test_retrieve_knowledge_applies_reranker_when_present() -> None:
    results = [make_result("a"), make_result("b")]
    use_case = RetrieveKnowledge(FakeRetriever(results), FakeReranker())

    output = use_case("query", make_scope(), top_k=5)

    assert [r.chunk_id for r in output] == ["b", "a"]


def test_retrieve_knowledge_falls_back_when_reranker_fails() -> None:
    results = [make_result("a"), make_result("b")]
    use_case = RetrieveKnowledge(FakeRetriever(results), FakeReranker(fail=True))

    output = use_case("query", make_scope(), top_k=5)

    assert [r.chunk_id for r in output] == ["a", "b"]


def test_retrieve_knowledge_skips_reranker_when_no_results() -> None:
    use_case = RetrieveKnowledge(FakeRetriever([]), FakeReranker(fail=True))

    output = use_case("query", make_scope(), top_k=5)

    assert output == []
