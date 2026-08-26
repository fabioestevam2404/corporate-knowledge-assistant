from cka.evaluation.generation_metrics import (
    citation_accuracy,
    citation_completeness,
    matches_expected_behavior,
)


def test_citation_accuracy_all_correct() -> None:
    assert citation_accuracy(["SRC-1"], ["SRC-1"]) == 1.0


def test_citation_accuracy_partial() -> None:
    assert citation_accuracy(["SRC-1", "SRC-2"], ["SRC-1"]) == 0.5


def test_citation_accuracy_no_citations_is_zero() -> None:
    assert citation_accuracy([], ["SRC-1"]) == 0.0


def test_citation_accuracy_correct_abstention_is_perfect() -> None:
    # Regression test for a real defect found once this ran against a real
    # LLM (see docs/release-gate/PROGRESS.md, Block 4/Sprint 15): citing
    # nothing when nothing was expected is a correct abstention, not a
    # citation failure -- this used to return 0.0, silently penalizing
    # correct abstention and dragging down the aggregate citation_accuracy
    # score for cases that had nothing to do with citation quality at all.
    # citation_completeness already handled this symmetric case correctly
    # (see test_citation_completeness_no_expected_sources_is_perfect).
    assert citation_accuracy([], []) == 1.0


def test_citation_completeness_all_found() -> None:
    assert citation_completeness(["SRC-1", "SRC-2"], ["SRC-1", "SRC-2"]) == 1.0


def test_citation_completeness_partial() -> None:
    assert citation_completeness(["SRC-1"], ["SRC-1", "SRC-2"]) == 0.5


def test_citation_completeness_no_expected_sources_is_perfect() -> None:
    assert citation_completeness([], []) == 1.0


def test_matches_expected_behavior_grounded_answer() -> None:
    assert matches_expected_behavior(grounded=True, expected_behavior="answer") is True


def test_matches_expected_behavior_correct_abstention() -> None:
    assert matches_expected_behavior(grounded=False, expected_behavior="abstain") is True


def test_matches_expected_behavior_wrongly_abstained() -> None:
    assert matches_expected_behavior(grounded=False, expected_behavior="answer") is False


def test_matches_expected_behavior_wrongly_answered() -> None:
    assert matches_expected_behavior(grounded=True, expected_behavior="abstain") is False
