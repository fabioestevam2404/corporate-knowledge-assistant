import uuid
from collections.abc import Callable, Generator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cka.core.config import get_settings
from cka.infrastructure.database.connection import make_engine, make_session_factory
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.embeddings.sentence_transformer_embedding_service import (
    SentenceTransformerEmbeddingService,
)
from cka.infrastructure.security.jwt import create_access_token

# Shared across tests/integration, tests/security and tests/observability —
# fixtures live at this top level so all three can use them.


@pytest.fixture(scope="session")
def engine() -> Engine:
    return make_engine(get_settings().database_url)


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    session_factory = make_session_factory(engine)
    session = session_factory()
    try:
        yield session
        session.rollback()
    finally:
        session.execute(text("DELETE FROM document_chunks"))
        session.execute(text("DELETE FROM documents"))
        session.execute(text("DELETE FROM users"))
        session.commit()
        session.close()


@pytest.fixture(scope="session")
def real_embedding_service() -> EmbeddingService:
    """Session-scoped so the real model loads once per test run, not per test."""
    return SentenceTransformerEmbeddingService()


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    """Real JWTs signed with the app's real (dev-default) secret — for tests
    that only need a valid role claim, not a real DB user row (that's what
    /auth/login integration tests exist for separately).
    """

    def _make(role: str, user_id: str | None = None) -> dict[str, str]:
        settings = get_settings()
        token = create_access_token(
            user_id or str(uuid.uuid4()), role, settings.jwt_secret_key, expire_minutes=30
        )
        return {"Authorization": f"Bearer {token}"}

    return _make
