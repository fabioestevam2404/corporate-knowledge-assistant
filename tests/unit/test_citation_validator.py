from cka.application.rag.citation_validator import validate_citations
from cka.domain.evidence import Evidence


def make_evidence(chunk_id: str) -> Evidence:
    return Evidence(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="SRC-1",
        content="content",
        page_number=None,
        score=0.9,
    )


def test_valid_citations_are_kept() -> None:
    evidences = [make_evidence("c1"), make_evidence("c2")]

    result = validate_citations(["c1"], evidences)

    assert result == ["c1"]


def test_hallucinated_citation_is_dropped() -> None:
    evidences = [make_evidence("c1")]

    result = validate_citations(["c1", "does-not-exist"], evidences)

    assert result == ["c1"]


def test_all_hallucinated_citations_returns_empty() -> None:
    evidences = [make_evidence("c1")]

    assert validate_citations(["ghost"], evidences) == []


def test_no_citations_returns_empty() -> None:
    assert validate_citations([], [make_evidence("c1")]) == []
