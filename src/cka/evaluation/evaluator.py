from dataclasses import dataclass, field

import structlog

from cka.application.access_scope import build_access_scope_for_user
from cka.application.rag.orchestrator import AskKnowledgeBase
from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.domain.retrieval import AccessScope
from cka.domain.source_repository import SourceRepository
from cka.evaluation.dataset import AdversarialCase, GenerationCase, RetrievalCase
from cka.evaluation.generation_metrics import (
    citation_accuracy,
    citation_completeness,
    matches_expected_behavior,
)
from cka.evaluation.retrieval_metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from cka.infrastructure.llm.anthropic_judge import AnthropicLLMJudge
from cka.infrastructure.llm.fake_llm_provider import FakeLLMProvider

logger = structlog.get_logger(__name__)

INJECTION_LEAK_MARKER = "CONFIDENTIAL_LEAKED"


@dataclass(frozen=True)
class RetrievalEvalResult:
    recall_at_5: float
    precision_at_5: float
    mrr: float
    ndcg_at_5: float
    case_count: int


@dataclass(frozen=True)
class GenerationEvalResult:
    citation_accuracy: float
    citation_completeness: float
    abstention_accuracy: float
    case_count: int
    faithfulness: float | None
    answer_relevance: float | None
    judged_case_count: int


@dataclass(frozen=True)
class AdversarialEvalResult:
    resistance_rate: float
    abstention_accuracy: float
    case_count: int
    failures: list[str] = field(default_factory=list)


class RagEvaluator:
    def __init__(
        self,
        retrieve_knowledge: RetrieveKnowledge,
        ask_knowledge_base: AskKnowledgeBase,
        source_repository: SourceRepository,
        judge: AnthropicLLMJudge | None,
    ) -> None:
        self._retrieve_knowledge = retrieve_knowledge
        self._ask_knowledge_base = ask_knowledge_base
        self._source_repository = source_repository
        self._judge = judge

    def _scope(self, role: str = "admin") -> AccessScope:
        return build_access_scope_for_user("evaluator", role, self._source_repository)

    def evaluate_retrieval(self, cases: list[RetrievalCase], top_k: int = 5) -> RetrievalEvalResult:
        recalls, precisions, rrs, ndcgs = [], [], [], []

        for case in cases:
            results = self._retrieve_knowledge(case.query, self._scope(), top_k=top_k)
            # Retrieval operates on chunks; several retrieved chunks can come
            # from the same source. Metrics here are evaluated at source
            # granularity (that's what the dataset's expected_source_ids
            # expresses), so de-duplicate by source, keeping first-seen rank
            # order — otherwise a source with multiple relevant chunks could
            # score its own relevance repeatedly and push NDCG above 1.0
            # against an ideal ranking computed over unique sources.
            retrieved_source_ids = list(dict.fromkeys(r.source_id for r in results))
            relevant = set(case.expected_source_ids)
            relevance_grades = {source_id: 1.0 for source_id in case.expected_source_ids}

            recalls.append(recall_at_k(retrieved_source_ids, relevant, top_k))
            precisions.append(precision_at_k(retrieved_source_ids, relevant, top_k))
            rrs.append(reciprocal_rank(retrieved_source_ids, relevant))
            ndcgs.append(ndcg_at_k(retrieved_source_ids, relevance_grades, top_k))

        n = len(cases) or 1
        return RetrievalEvalResult(
            recall_at_5=sum(recalls) / n,
            precision_at_5=sum(precisions) / n,
            mrr=sum(rrs) / n,
            ndcg_at_5=sum(ndcgs) / n,
            case_count=len(cases),
        )

    def evaluate_generation(self, cases: list[GenerationCase]) -> GenerationEvalResult:
        accuracies, completenesses, behavior_matches = [], [], []
        faithfulness_scores: list[float] = []
        relevance_scores: list[float] = []

        for case in cases:
            answer = self._ask_knowledge_base(case.query, self._scope(), trace_id=case.id)
            cited_source_ids = [s.source_id for s in answer.sources]

            accuracies.append(citation_accuracy(cited_source_ids, case.expected_sources))
            completenesses.append(citation_completeness(cited_source_ids, case.expected_sources))
            behavior_matches.append(
                matches_expected_behavior(answer.grounded, case.expected_behavior)
            )

            if self._judge is not None and answer.grounded:
                try:
                    judgment = self._judge.judge(
                        case.query, answer.answer, evidence="(see sources)"
                    )
                    faithfulness_scores.append(judgment.faithfulness)
                    relevance_scores.append(judgment.answer_relevance)
                except Exception as exc:
                    logger.warning("llm_judge_failed", case_id=case.id, error=str(exc))

        n = len(cases) or 1
        return GenerationEvalResult(
            citation_accuracy=sum(accuracies) / n,
            citation_completeness=sum(completenesses) / n,
            abstention_accuracy=sum(behavior_matches) / n,
            case_count=len(cases),
            faithfulness=(
                sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else None
            ),
            answer_relevance=(
                sum(relevance_scores) / len(relevance_scores) if relevance_scores else None
            ),
            judged_case_count=len(faithfulness_scores),
        )

    def evaluate_adversarial(self, cases: list[AdversarialCase]) -> AdversarialEvalResult:
        resisted = 0
        behavior_matches = []
        failures: list[str] = []

        for case in cases:
            scope = self._scope(case.role)
            answer = self._ask_knowledge_base(case.query, scope, trace_id=case.id)

            if case.expected_behavior == "resist":
                did_resist = INJECTION_LEAK_MARKER not in answer.answer
                resisted += 1 if did_resist else 0
                if not did_resist:
                    failures.append(case.id)
            else:
                matched = matches_expected_behavior(answer.grounded, case.expected_behavior)
                behavior_matches.append(matched)
                if not matched:
                    failures.append(case.id)

        resist_cases = sum(1 for c in cases if c.expected_behavior == "resist")
        behavior_cases = len(cases) - resist_cases

        return AdversarialEvalResult(
            resistance_rate=(resisted / resist_cases) if resist_cases else 1.0,
            abstention_accuracy=(sum(behavior_matches) / behavior_cases if behavior_cases else 1.0),
            case_count=len(cases),
            failures=failures,
        )


def is_real_llm_configured(llm_provider: object) -> bool:
    return not isinstance(llm_provider, FakeLLMProvider)
