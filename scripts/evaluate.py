"""Runs the real Golden Dataset (Sprint 10) against the real retriever/RAG
orchestrator and writes reports/evaluation_latest.{json,md}.

Requires the sample corpus already ingested (see tests/integration/seeding.py
or `docker compose up -d db` + a manual seed). Exits non-zero if the
evaluation gate (evaluation_gate thresholds in Settings) is violated.

Run with: uv run python scripts/evaluate.py
"""

import sys
from pathlib import Path

from cka.application.rag.context_builder import ContextBuilder
from cka.application.rag.orchestrator import AskKnowledgeBase
from cka.application.rag.prompt_builder import PromptBuilder
from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.core.config import get_settings
from cka.domain.llm_provider import LLMProvider, LLMResponse
from cka.evaluation.dataset import (
    load_adversarial_cases,
    load_generation_cases,
    load_retrieval_cases,
)
from cka.evaluation.evaluator import RagEvaluator
from cka.evaluation.gate import check_gate
from cka.evaluation.report import build_report_dict, write_json_report, write_markdown_report
from cka.infrastructure.database.connection import make_engine, make_session_factory
from cka.infrastructure.embeddings.sentence_transformer_embedding_service import (
    SentenceTransformerEmbeddingService,
)
from cka.infrastructure.llm.anthropic_judge import AnthropicLLMJudge
from cka.infrastructure.llm.anthropic_provider import AnthropicProvider
from cka.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from cka.infrastructure.ranking.cross_encoder_reranker import CrossEncoderReranker
from cka.infrastructure.retrieval.hybrid_retriever import HybridRetriever
from cka.infrastructure.retrieval.pgvector_retriever import PgVectorRetriever
from cka.infrastructure.retrieval.postgres_keyword_retriever import PostgresKeywordRetriever
from cka.infrastructure.sources.yaml_source_repository import YamlSourceRepository

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    settings = get_settings()

    engine = make_engine(settings.database_url)
    session = make_session_factory(engine)()

    source_repository = YamlSourceRepository(settings.sources_registry_path)
    embedding_service = SentenceTransformerEmbeddingService(settings.embedding_model_name)
    reranker = CrossEncoderReranker(settings.reranker_model_name)

    hybrid = HybridRetriever(
        PgVectorRetriever(session, embedding_service),
        PostgresKeywordRetriever(session),
        candidate_k=settings.hybrid_candidate_k,
        rrf_k=settings.rrf_k,
    )
    retrieve_knowledge = RetrieveKnowledge(hybrid, reranker)

    real_llm_used = bool(settings.anthropic_api_key)
    llm_provider: LLMProvider
    judge: AnthropicLLMJudge | None
    if settings.anthropic_api_key:
        llm_provider = AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
        )
        judge = AnthropicLLMJudge(settings.anthropic_api_key, settings.anthropic_model)
    else:
        print(
            "ANTHROPIC_API_KEY not set — using FakeLLMProvider; faithfulness/answer_relevance "
            "will be skipped (not faked)."
        )
        llm_provider = FakeLLMProvider(
            LLMResponse(answer="ANTHROPIC_API_KEY not configured.", citations=[])
        )
        judge = None

    ask_knowledge_base = AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(max_context_tokens=settings.max_context_tokens),
        PromptBuilder(),
        llm_provider,
        min_retrieval_score=settings.rag_min_retrieval_score,
        score_threshold=settings.confidence_score_threshold,
        high_min_evidence=settings.confidence_high_min_evidence,
        top_k=settings.retrieval_top_k,
    )

    evaluator = RagEvaluator(retrieve_knowledge, ask_knowledge_base, source_repository, judge)

    retrieval_cases = load_retrieval_cases(REPO_ROOT / "data" / "evaluation" / "retrieval.yaml")
    generation_cases = load_generation_cases(REPO_ROOT / "data" / "evaluation" / "generation.yaml")
    adversarial_cases = load_adversarial_cases(
        REPO_ROOT / "data" / "evaluation" / "adversarial.yaml"
    )

    print(f"Running {len(retrieval_cases)} retrieval cases...")
    retrieval_result = evaluator.evaluate_retrieval(retrieval_cases, top_k=settings.retrieval_top_k)

    print(f"Running {len(generation_cases)} generation cases...")
    generation_result = evaluator.evaluate_generation(generation_cases)

    print(f"Running {len(adversarial_cases)} adversarial cases...")
    adversarial_result = evaluator.evaluate_adversarial(adversarial_cases)

    report = build_report_dict(
        retrieval_result, generation_result, adversarial_result, real_llm_used=real_llm_used
    )
    write_json_report(report, REPO_ROOT / "reports" / "evaluation_latest.json")
    write_markdown_report(report, REPO_ROOT / "reports" / "evaluation_latest.md")

    print("\n--- Results ---")
    print(
        f"Retrieval:   Recall@5={retrieval_result.recall_at_5:.3f} MRR={retrieval_result.mrr:.3f} "
        f"NDCG@5={retrieval_result.ndcg_at_5:.3f}"
    )
    print(
        f"Generation:  CitationAccuracy={generation_result.citation_accuracy:.3f} "
        f"AbstentionAccuracy={generation_result.abstention_accuracy:.3f} "
        f"Faithfulness={generation_result.faithfulness} "
        f"AnswerRelevance={generation_result.answer_relevance}"
    )
    print(
        f"Adversarial: ResistanceRate={adversarial_result.resistance_rate:.3f} "
        f"AbstentionAccuracy={adversarial_result.abstention_accuracy:.3f} "
        f"Failures={adversarial_result.failures}"
    )

    violations = check_gate(retrieval_result, generation_result, settings, real_llm_used)
    if violations:
        print("\nEVALUATION GATE FAILED:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("\nEvaluation gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
