from sqlalchemy.orm import Session

from cka.domain.retrieval import AccessScope, RetrievalQuery
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.retrieval.pgvector_retriever import PgVectorRetriever
from tests.integration.seeding import ALL_SOURCE_IDS, seed_full_corpus


def test_semantic_retrieval_ranks_the_topically_relevant_document_first(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    retriever = PgVectorRetriever(db_session, real_embedding_service)
    scope = AccessScope(user_id="test-user", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    results = retriever.retrieve(
        RetrievalQuery(
            text="How many days per week can I work remotely?", top_k=3, access_scope=scope
        )
    )

    assert len(results) > 0
    assert results[0].source_id == "SRC-SAMPLE-001"


def test_semantic_retrieval_finds_security_policy_for_password_question(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    retriever = PgVectorRetriever(db_session, real_embedding_service)
    scope = AccessScope(user_id="test-user", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    results = retriever.retrieve(
        RetrievalQuery(text="What are the password requirements?", top_k=3, access_scope=scope)
    )

    assert results[0].source_id == "SRC-SAMPLE-002"


def test_access_scope_excludes_sources_outside_allowed_ids(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    retriever = PgVectorRetriever(db_session, real_embedding_service)
    # Deliberately excludes SRC-SAMPLE-001 (remote work) even though the
    # query is squarely about remote work — this is the ACL-before-retrieval
    # contract the roadmap's Sprint 15 authorization test depends on.
    scope = AccessScope(
        user_id="test-user",
        role="employee",
        allowed_source_ids=frozenset({"SRC-SAMPLE-002", "SRC-SAMPLE-003", "SRC-SAMPLE-004"}),
    )

    results = retriever.retrieve(
        RetrievalQuery(text="remote work policy days per week", top_k=5, access_scope=scope)
    )

    assert all(r.source_id != "SRC-SAMPLE-001" for r in results)
