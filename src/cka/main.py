from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from cka.api.errors import register_exception_handlers
from cka.api.routes.ask import router as ask_router
from cka.api.routes.auth import router as auth_router
from cka.api.routes.documents import router as documents_router
from cka.api.routes.health import router as health_router
from cka.api.routes.metrics import router as metrics_router
from cka.api.routes.retrieve import router as retrieve_router
from cka.core.config import get_settings
from cka.domain.llm_provider import LLMResponse
from cka.infrastructure.database.connection import make_engine
from cka.infrastructure.embeddings.sentence_transformer_embedding_service import (
    SentenceTransformerEmbeddingService,
)
from cka.infrastructure.llm.anthropic_provider import AnthropicProvider
from cka.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from cka.infrastructure.ranking.cross_encoder_reranker import CrossEncoderReranker
from cka.infrastructure.security.rate_limiter import RateLimiter
from cka.infrastructure.sources.yaml_source_repository import YamlSourceRepository
from cka.observability.logging import configure_logging
from cka.observability.middleware import RequestContextMiddleware
from cka.observability.tracing import configure_tracing

configure_logging(get_settings().log_level)
configure_tracing(get_settings().otlp_endpoint, get_settings().otel_traces_enabled)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    app.state.engine = make_engine(settings.database_url)
    app.state.source_repository = YamlSourceRepository(settings.sources_registry_path)
    # Loaded once at startup — reloading a transformer model per request would
    # make every retrieval request pay full model-load latency.
    app.state.embedding_service = SentenceTransformerEmbeddingService(settings.embedding_model_name)
    app.state.reranker = CrossEncoderReranker(settings.reranker_model_name)
    app.state.rate_limiter = RateLimiter(max_requests=settings.rate_limit_per_minute)

    if settings.anthropic_api_key:
        app.state.llm_provider = AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
        )
    else:
        # No key configured: /ask still works end-to-end (retrieval, ACL,
        # abstention), it just can't generate real answers. This only
        # matters for local dev/tests — real deployments must set the key.
        app.state.llm_provider = FakeLLMProvider(
            response=LLMResponse(
                answer="ANTHROPIC_API_KEY not configured — no real answer available.",
                citations=[],
            )
        )

    yield
    app.state.engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Corporate Knowledge Assistant", lifespan=lifespan)

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(retrieve_router)
    app.include_router(ask_router)
    app.include_router(documents_router)
    app.include_router(metrics_router)
    FastAPIInstrumentor.instrument_app(app)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Corporate Knowledge Assistant API", "status": "running"}

    return app


app = create_app()
