from cka.core.config import Settings
from cka.evaluation.evaluator import GenerationEvalResult, RetrievalEvalResult
from cka.evaluation.gate import check_gate


def make_settings(**overrides: object) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def make_retrieval(recall_at_5: float = 1.0) -> RetrievalEvalResult:
    return RetrievalEvalResult(
        recall_at_5=recall_at_5, precision_at_5=1.0, mrr=1.0, ndcg_at_5=1.0, case_count=5
    )


def make_generation(
    citation_accuracy: float = 1.0,
    faithfulness: float | None = None,
    answer_relevance: float | None = None,
) -> GenerationEvalResult:
    return GenerationEvalResult(
        citation_accuracy=citation_accuracy,
        citation_completeness=1.0,
        abstention_accuracy=1.0,
        case_count=5,
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
        judged_case_count=0 if faithfulness is None else 5,
    )


def test_passing_metrics_produce_no_violations() -> None:
    violations = check_gate(
        make_retrieval(), make_generation(), make_settings(), real_llm_used=True
    )

    assert violations == []


def test_low_recall_is_a_violation_even_without_a_real_llm() -> None:
    settings = make_settings(evaluation_min_recall_at_5=0.9)

    violations = check_gate(
        make_retrieval(recall_at_5=0.5), make_generation(), settings, real_llm_used=False
    )

    assert any("recall_at_5" in v for v in violations)


def test_low_citation_accuracy_is_a_violation_when_real_llm_used() -> None:
    settings = make_settings(evaluation_min_citation_accuracy=0.9)

    violations = check_gate(
        make_retrieval(),
        make_generation(citation_accuracy=0.5),
        settings,
        real_llm_used=True,
    )

    assert any("citation_accuracy" in v for v in violations)


def test_generation_metrics_skipped_without_a_real_llm() -> None:
    # FakeLLMProvider never cites anything — citation_accuracy would be 0.0
    # unconditionally, which must not fail the gate when there's no real LLM
    # in play at all.
    settings = make_settings(evaluation_min_citation_accuracy=0.9)

    violations = check_gate(
        make_retrieval(),
        make_generation(citation_accuracy=0.0),
        settings,
        real_llm_used=False,
    )

    assert violations == []


def test_faithfulness_not_checked_when_no_llm_judged_any_case() -> None:
    settings = make_settings(evaluation_min_faithfulness=0.9)

    violations = check_gate(
        make_retrieval(), make_generation(faithfulness=None), settings, real_llm_used=True
    )

    assert violations == []


def test_low_faithfulness_is_a_violation_when_judged() -> None:
    settings = make_settings(evaluation_min_faithfulness=0.9)

    violations = check_gate(
        make_retrieval(),
        make_generation(faithfulness=0.3, answer_relevance=0.9),
        settings,
        real_llm_used=True,
    )

    assert any("faithfulness" in v for v in violations)
