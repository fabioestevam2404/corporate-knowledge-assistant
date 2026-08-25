from cka.core.config import Settings
from cka.evaluation.evaluator import GenerationEvalResult, RetrievalEvalResult


def check_gate(
    retrieval: RetrievalEvalResult,
    generation: GenerationEvalResult,
    settings: Settings,
    real_llm_used: bool,
) -> list[str]:
    """Fails loudly, not silently, when a real evaluation run misses a
    threshold (ADR-010) — returns the list of violations (empty = pass).

    Recall@5 never depends on an LLM and is always checked. Citation
    accuracy, abstention accuracy, faithfulness and answer relevance all
    depend on what the LLM actually generates — with `FakeLLMProvider`
    (no ANTHROPIC_API_KEY) it never cites anything, which would make these
    metrics fail permanently and meaninglessly. They're only checked when
    a real LLM produced the answers being scored.
    """
    violations = []

    if retrieval.recall_at_5 < settings.evaluation_min_recall_at_5:
        violations.append(
            f"recall_at_5 {retrieval.recall_at_5:.3f} < {settings.evaluation_min_recall_at_5}"
        )

    if not real_llm_used:
        return violations

    if generation.citation_accuracy < settings.evaluation_min_citation_accuracy:
        violations.append(
            f"citation_accuracy {generation.citation_accuracy:.3f} "
            f"< {settings.evaluation_min_citation_accuracy}"
        )

    if generation.faithfulness is not None and (
        generation.faithfulness < settings.evaluation_min_faithfulness
    ):
        violations.append(
            f"faithfulness {generation.faithfulness:.3f} < {settings.evaluation_min_faithfulness}"
        )

    if generation.answer_relevance is not None and (
        generation.answer_relevance < settings.evaluation_min_answer_relevance
    ):
        violations.append(
            f"answer_relevance {generation.answer_relevance:.3f} "
            f"< {settings.evaluation_min_answer_relevance}"
        )

    return violations
