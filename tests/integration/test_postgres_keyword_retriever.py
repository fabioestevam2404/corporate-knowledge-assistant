from sqlalchemy.orm import Session

from cka.domain.retrieval import AccessScope, RetrievalQuery
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.retrieval.postgres_keyword_retriever import PostgresKeywordRetriever
from tests.integration.seeding import ALL_SOURCE_IDS, seed_full_corpus


def test_keyword_search_finds_exact_term_via_full_text_search(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    retriever = PostgresKeywordRetriever(db_session)
    scope = AccessScope(user_id="test-user", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    results = retriever.retrieve(
        RetrievalQuery(text="reimbursement deadline", top_k=3, access_scope=scope)
    )

    assert len(results) > 0
    assert results[0].source_id == "SRC-SAMPLE-004"


def test_keyword_search_respects_access_scope(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    retriever = PostgresKeywordRetriever(db_session)
    scope = AccessScope(
        user_id="test-user", role="employee", allowed_source_ids=frozenset({"SRC-SAMPLE-001"})
    )

    results = retriever.retrieve(
        RetrievalQuery(text="reimbursement deadline", top_k=5, access_scope=scope)
    )

    assert results == []


def test_keyword_search_returns_empty_for_no_match(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    seed_full_corpus(db_session, real_embedding_service)
    retriever = PostgresKeywordRetriever(db_session)
    scope = AccessScope(user_id="test-user", role="employee", allowed_source_ids=ALL_SOURCE_IDS)

    results = retriever.retrieve(
        RetrievalQuery(text="quantum photosynthesis unicorn", top_k=5, access_scope=scope)
    )

    assert results == []
