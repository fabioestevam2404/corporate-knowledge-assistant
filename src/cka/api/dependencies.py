from collections.abc import Callable, Generator
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from cka.application.access_scope import build_access_scope_for_user
from cka.application.authenticate_user import AuthenticateUser
from cka.application.delete_document import DeleteDocument
from cka.application.ingest_document import IngestDocument
from cka.application.process_document import ProcessDocument
from cka.application.rag.context_builder import ContextBuilder
from cka.application.rag.orchestrator import AskKnowledgeBase
from cka.application.rag.prompt_builder import PromptBuilder
from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.application.validate_source import ValidateSource
from cka.core.config import get_settings
from cka.domain.chunk_repository import ChunkRepository
from cka.domain.document_repository import DocumentRepository
from cka.domain.llm_provider import LLMProvider
from cka.domain.ranking import Reranker
from cka.domain.retrieval import AccessScope, Retriever
from cka.domain.source_repository import SourceRepository
from cka.domain.user import has_permission
from cka.domain.user_repository import UserRepository
from cka.infrastructure.database.chunk_repository import SqlAlchemyChunkRepository
from cka.infrastructure.database.connection import make_session_factory
from cka.infrastructure.database.document_repository import SqlAlchemyDocumentRepository
from cka.infrastructure.database.user_repository import SqlAlchemyUserRepository
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.processing.chunker import TextChunker
from cka.infrastructure.processing.pdf_loader import PdfDocumentLoader
from cka.infrastructure.processing.text_loader import PlainTextLoader
from cka.infrastructure.retrieval.hybrid_retriever import HybridRetriever
from cka.infrastructure.retrieval.pgvector_retriever import PgVectorRetriever
from cka.infrastructure.retrieval.postgres_keyword_retriever import PostgresKeywordRetriever
from cka.infrastructure.security.jwt import InvalidTokenError, TokenPayload, decode_access_token
from cka.infrastructure.security.rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = make_session_factory(request.app.state.engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_embedding_service(request: Request) -> EmbeddingService:
    return request.app.state.embedding_service  # type: ignore[no-any-return]


def get_reranker(request: Request) -> Reranker:
    return request.app.state.reranker  # type: ignore[no-any-return]


def get_source_repository(request: Request) -> SourceRepository:
    return request.app.state.source_repository  # type: ignore[no-any-return]


def get_llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm_provider  # type: ignore[no-any-return]


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter  # type: ignore[no-any-return]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    try:
        return decode_access_token(credentials.credentials, get_settings().jwt_secret_key)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from exc


DbSession = Annotated[Session, Depends(get_db_session)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
RerankerDep = Annotated[Reranker, Depends(get_reranker)]
SourceRepositoryDep = Annotated[SourceRepository, Depends(get_source_repository)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
CurrentUserDep = Annotated[TokenPayload, Depends(get_current_user)]


def enforce_rate_limit(current_user: CurrentUserDep, rate_limiter: RateLimiterDep) -> None:
    if not rate_limiter.allow(current_user.user_id):
        logger.warning("rate_limit_exceeded", user_id=current_user.user_id)
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")


RateLimitDep = Annotated[None, Depends(enforce_rate_limit)]


def require_permission(permission: str) -> Callable[[CurrentUserDep], TokenPayload]:
    """RBAC gate for endpoints beyond retrieval/generation (e.g. /documents).
    Document-level ACL (which sources a user can retrieve from) is separate
    and always enforced via AccessScope — see get_access_scope below.
    """

    def checker(current_user: CurrentUserDep) -> TokenPayload:
        if not has_permission(current_user.role, permission):
            logger.warning(
                "authorization_denied",
                user_id=current_user.user_id,
                role=current_user.role,
                permission=permission,
            )
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return current_user

    return checker


def get_access_scope(
    current_user: CurrentUserDep, source_repository: SourceRepositoryDep
) -> AccessScope:
    return build_access_scope_for_user(current_user.user_id, current_user.role, source_repository)


def get_user_repository(session: DbSession) -> UserRepository:
    return SqlAlchemyUserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_authenticate_user(user_repository: UserRepositoryDep) -> AuthenticateUser:
    settings = get_settings()
    return AuthenticateUser(
        user_repository, settings.jwt_secret_key, settings.access_token_expire_minutes
    )


AuthenticateUserDep = Annotated[AuthenticateUser, Depends(get_authenticate_user)]


def get_retriever(session: DbSession, embedding_service: EmbeddingServiceDep) -> Retriever:
    settings = get_settings()
    vector_retriever = PgVectorRetriever(session, embedding_service)
    keyword_retriever = PostgresKeywordRetriever(session)
    return HybridRetriever(
        vector_retriever,
        keyword_retriever,
        candidate_k=settings.hybrid_candidate_k,
        rrf_k=settings.rrf_k,
    )


AccessScopeDep = Annotated[AccessScope, Depends(get_access_scope)]
RetrieverDep = Annotated[Retriever, Depends(get_retriever)]


def get_retrieve_knowledge(retriever: RetrieverDep, reranker: RerankerDep) -> RetrieveKnowledge:
    return RetrieveKnowledge(retriever, reranker)


RetrieveKnowledgeDep = Annotated[RetrieveKnowledge, Depends(get_retrieve_knowledge)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]


def get_ask_knowledge_base(
    retrieve_knowledge: RetrieveKnowledgeDep, llm_provider: LLMProviderDep
) -> AskKnowledgeBase:
    settings = get_settings()
    return AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(max_context_tokens=settings.max_context_tokens),
        PromptBuilder(),
        llm_provider,
        min_retrieval_score=settings.rag_min_retrieval_score,
        score_threshold=settings.confidence_score_threshold,
        high_min_evidence=settings.confidence_high_min_evidence,
        top_k=settings.retrieval_top_k,
    )


AskKnowledgeBaseDep = Annotated[AskKnowledgeBase, Depends(get_ask_knowledge_base)]


def get_document_repository(session: DbSession) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(session)


def get_chunk_repository(session: DbSession) -> ChunkRepository:
    return SqlAlchemyChunkRepository(session)


DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
ChunkRepositoryDep = Annotated[ChunkRepository, Depends(get_chunk_repository)]


def get_ingest_document(
    source_repository: SourceRepositoryDep, document_repository: DocumentRepositoryDep
) -> IngestDocument:
    return IngestDocument(ValidateSource(source_repository), document_repository)


def get_process_document(
    embedding_service: EmbeddingServiceDep, chunk_repository: ChunkRepositoryDep
) -> ProcessDocument:
    settings = get_settings()
    return ProcessDocument(
        loaders=[PlainTextLoader(), PdfDocumentLoader()],
        chunker=TextChunker(chunk_size=settings.chunk_size, overlap=settings.chunk_overlap),
        embedding_service=embedding_service,
        chunk_repository=chunk_repository,
    )


def get_delete_document(
    document_repository: DocumentRepositoryDep, chunk_repository: ChunkRepositoryDep
) -> DeleteDocument:
    return DeleteDocument(document_repository, chunk_repository)


IngestDocumentDep = Annotated[IngestDocument, Depends(get_ingest_document)]
ProcessDocumentDep = Annotated[ProcessDocument, Depends(get_process_document)]
DeleteDocumentDep = Annotated[DeleteDocument, Depends(get_delete_document)]
