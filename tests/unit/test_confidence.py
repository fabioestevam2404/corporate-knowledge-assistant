from cka.application.rag.confidence import HIGH, LOW, MEDIUM, compute_confidence
from cka.domain.evidence import Evidence


def make_evidence(chunk_id: str, score: float) -> Evidence:
    return Evidence(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="SRC-1",
        content="content",
        page_number=None,
        score=score,
    )


def test_zero_valid_citations_is_low() -> None:
    evidences = [make_evidence("c1", 0.9)]

    result = compute_confidence(
        evidences, total_citations=1, valid_citations=0, score_threshold=0.6, high_min_evidence=2
    )

    assert result == LOW


def test_all_valid_citations_with_enough_strong_evidence_is_high() -> None:
    evidences = [make_evidence("c1", 0.9), make_evidence("c2", 0.8)]

    result = compute_confidence(
        evidences, total_citations=2, valid_citations=2, score_threshold=0.6, high_min_evidence=2
    )

    assert result == HIGH


def test_single_evidence_is_medium_even_if_valid() -> None:
    evidences = [make_evidence("c1", 0.95)]

    result = compute_confidence(
        evidences, total_citations=1, valid_citations=1, score_threshold=0.6, high_min_evidence=2
    )

    assert result == MEDIUM


def test_partial_valid_citations_is_medium() -> None:
    evidences = [make_evidence("c1", 0.9), make_evidence("c2", 0.8)]

    result = compute_confidence(
        evidences, total_citations=2, valid_citations=1, score_threshold=0.6, high_min_evidence=2
    )

    assert result == MEDIUM


def test_weak_evidence_scores_keep_it_medium_not_high() -> None:
    evidences = [make_evidence("c1", 0.3), make_evidence("c2", 0.2)]

    result = compute_confidence(
        evidences, total_citations=2, valid_citations=2, score_threshold=0.6, high_min_evidence=2
    )

    assert result == MEDIUM
