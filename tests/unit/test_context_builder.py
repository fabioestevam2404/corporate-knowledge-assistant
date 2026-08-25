from cka.application.rag.context_builder import ContextBuilder
from cka.domain.evidence import Evidence


def make_evidence(chunk_id: str, content: str, page_number: int | None = None) -> Evidence:
    return Evidence(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="SRC-1",
        content=content,
        page_number=page_number,
        score=0.9,
    )


def test_build_includes_all_evidence_when_under_budget() -> None:
    builder = ContextBuilder(max_context_tokens=6000)
    evidences = [make_evidence("c1", "first chunk"), make_evidence("c2", "second chunk")]

    context, included = builder.build(evidences)

    assert len(included) == 2
    assert "c1" in context
    assert "c2" in context
    assert "SOURCE_ID: SRC-1" in context
    assert "CHUNK_ID: c1" in context


def test_build_formats_page_number_as_n_a_when_absent() -> None:
    builder = ContextBuilder()
    context, _ = builder.build([make_evidence("c1", "content", page_number=None)])

    assert "PAGE: N/A" in context


def test_build_formats_real_page_number() -> None:
    builder = ContextBuilder()
    context, _ = builder.build([make_evidence("c1", "content", page_number=3)])

    assert "PAGE: 3" in context


def test_build_stops_before_exceeding_token_budget() -> None:
    # Each block is a few dozen tokens; force a tiny budget so only the
    # first evidence fits.
    builder = ContextBuilder(max_context_tokens=20)
    evidences = [
        make_evidence("c1", "short"),
        make_evidence("c2", "also fairly short content here"),
    ]

    _, included = builder.build(evidences)

    assert len(included) == 1
    assert included[0].chunk_id == "c1"


def test_build_always_includes_first_evidence_even_if_it_alone_exceeds_budget() -> None:
    builder = ContextBuilder(max_context_tokens=1)
    evidences = [make_evidence("c1", "this single chunk is larger than the tiny budget")]

    _, included = builder.build(evidences)

    assert len(included) == 1


def test_build_empty_evidence_list_returns_empty_context() -> None:
    builder = ContextBuilder()

    context, included = builder.build([])

    assert context == ""
    assert included == []
