from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_ONLY_JWT_SECRET = "dev-only-insecure-secret-change-me"
_MIN_JWT_SECRET_BYTES = 32  # matches PyJWT's own recommendation for HS256


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://cka:cka@localhost:5434/cka"

    sources_registry_path: str = "data/sources/registry.yaml"

    # Sprint 05 — chunking
    chunk_size: int = 1200
    chunk_overlap: int = 200

    # Sprint 05/07 — models (embedding dimension is pinned to 384 in the schema,
    # see infrastructure/database/models.py EMBEDDING_DIMENSION)
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Sprint 06 — retrieval
    retrieval_top_k: int = 5
    hybrid_candidate_k: int = 20
    rrf_k: int = 60

    # Sprint 08 — generation
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1000
    max_context_tokens: int = 6000
    max_query_length: int = 2000
    rag_min_retrieval_score: float = 0.50
    confidence_high_min_evidence: int = 2
    confidence_score_threshold: float = 0.6

    # Sprint 09 — security
    # Dev-only default. Real deployments MUST override via .env — never
    # commit a real secret. See docs/adr/ADR-009... (Block 4 doc set).
    jwt_secret_key: str = _DEV_ONLY_JWT_SECRET
    access_token_expire_minutes: int = 30
    rate_limit_per_minute: int = 60

    # Sprint 10 — evaluation
    evaluation_min_recall_at_5: float = 0.70
    evaluation_min_citation_accuracy: float = 0.90
    evaluation_min_faithfulness: float = 0.85
    evaluation_min_answer_relevance: float = 0.80

    # Sprint 11 — observability
    otlp_endpoint: str = "http://localhost:4317"
    otel_traces_enabled: bool = True

    @model_validator(mode="after")
    def _forbid_dev_jwt_secret_in_production(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret_key == _DEV_ONLY_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET_KEY is still the dev-only default — set a real secret "
                    "via the environment before running with ENVIRONMENT=production."
                )
            if len(self.jwt_secret_key.encode()) < _MIN_JWT_SECRET_BYTES:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {_MIN_JWT_SECRET_BYTES} bytes "
                    "in production (PyJWT's own minimum recommendation for HS256)."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
