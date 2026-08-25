from sqlalchemy.orm import Session

from cka.domain.retrieval import AccessScope, RetrievalQuery
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.retrieval.hybrid_retriever import HybridRetriever
from cka.infrastructure.retrieval.pgvector_retriever import PgVectorRetriever
from cka.infrastructure.retrieval.postgres_keyword_retriever import PostgresKeywordRetriever
from tests.integration.seeding import ALL_SOURCE_IDS, seed_full_corpus


def test_hybrid_retrieval_combines_vector_and_keyword_over_real_corpus(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    hybrid = HybridRetriever(
        PgVectorRetriever(db_session, real_embedding_service),
        PostgresKeywordRetriever(db_session),
        candidate_k=20,
        rrf_k=60,
    )
    scope = AccessScope(user_id="test-user", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    results = hybrid.retrieve(
        RetrievalQuery(
            text="expense reimbursement submission deadline", top_k=3, access_scope=scope
        )
    )

    assert len(results) > 0
    assert results[0].source_id == "SRC-SAMPLE-004"


def test_hybrid_retrieval_respects_access_scope_end_to_end(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    hybrid = HybridRetriever(
        PgVectorRetriever(db_session, real_embedding_service),
        PostgresKeywordRetriever(db_session),
        candidate_k=20,
        rrf_k=60,
    )
    scope = AccessScope(
        user_id="test-user",
        role="employee",
        allowed_source_ids=frozenset({"SRC-SAMPLE-002", "SRC-SAMPLE-003", "SRC-SAMPLE-004"}),
    )

    results = hybrid.retrieve(
        RetrievalQuery(text="remote work eligibility days per week", top_k=5, access_scope=scope)
    )

    assert all(r.source_id != "SRC-SAMPLE-001" for r in results)
