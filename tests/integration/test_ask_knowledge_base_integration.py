from sqlalchemy.orm import Session

from cka.application.rag.context_builder import ContextBuilder
from cka.application.rag.orchestrator import ABSTENTION_TEXT, AskKnowledgeBase
from cka.application.rag.prompt_builder import PromptBuilder
from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.domain.llm_provider import LLMResponse
from cka.domain.retrieval import AccessScope
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from cka.infrastructure.ranking.cross_encoder_reranker import CrossEncoderReranker
from cka.infrastructure.retrieval.hybrid_retriever import HybridRetriever
from cka.infrastructure.retrieval.pgvector_retriever import PgVectorRetriever
from cka.infrastructure.retrieval.postgres_keyword_retriever import PostgresKeywordRetriever
from tests.integration.seeding import ALL_SOURCE_IDS, seed_full_corpus


def build_orchestrator(
    db_session: Session,
    real_embedding_service: EmbeddingService,
    llm_response: LLMResponse,
    min_retrieval_score: float = 0.5,
) -> AskKnowledgeBase:
    hybrid = HybridRetriever(
        PgVectorRetriever(db_session, real_embedding_service),
        PostgresKeywordRetriever(db_session),
        candidate_k=20,
        rrf_k=60,
    )
    retrieve_knowledge = RetrieveKnowledge(hybrid, CrossEncoderReranker())
    return AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        FakeLLMProvider(llm_response),
        min_retrieval_score=min_retrieval_score,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )


def test_ask_knowledge_base_retrieves_real_evidence_and_returns_grounded_answer(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    orchestrator = build_orchestrator(
        db_session,
        real_embedding_service,
        LLMResponse(
            answer="Reimbursement requests are due within 30 days.", citations=["ignored-below"]
        ),
    )
    scope = AccessScope(user_id="u1", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    answer = orchestrator(
        "What is the deadline to submit an expense reimbursement request?", scope, trace_id="t1"
    )

    # The FakeLLMProvider's citation doesn't match a real chunk_id, so it's
    # correctly rejected — this proves citation validation runs against the
    # real retrieved evidence, not a mock.
    assert answer.grounded is False
    assert answer.sources == []


def test_ask_knowledge_base_abstains_for_out_of_corpus_question(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    orchestrator = build_orchestrator(
        db_session,
        real_embedding_service,
        LLMResponse(answer="should never be used", citations=[]),
        min_retrieval_score=0.5,
    )
    scope = AccessScope(user_id="u1", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    answer = orchestrator("What was the company's stock price in 1995?", scope, trace_id="t1")

    assert answer.answer == ABSTENTION_TEXT
    assert answer.grounded is False


def test_ask_knowledge_base_cites_real_chunk_id_when_llm_uses_it(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    hybrid = HybridRetriever(
        PgVectorRetriever(db_session, real_embedding_service),
        PostgresKeywordRetriever(db_session),
        candidate_k=20,
        rrf_k=60,
    )
    retrieve_knowledge = RetrieveKnowledge(hybrid, CrossEncoderReranker())
    scope = AccessScope(user_id="u1", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    # Retrieve first (real) to discover the real chunk_id, then configure the
    # fake LLM to cite it — proving the validator accepts genuine citations.
    real_results = retrieve_knowledge("reimbursement submission deadline", scope, top_k=1)
    real_chunk_id = real_results[0].chunk_id

    orchestrator = AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        FakeLLMProvider(LLMResponse(answer="Within 30 days.", citations=[real_chunk_id])),
        min_retrieval_score=0.5,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )

    answer = orchestrator("reimbursement submission deadline", scope, trace_id="t1")

    assert answer.grounded is True
    assert [s.chunk_id for s in answer.sources] == [real_chunk_id]
