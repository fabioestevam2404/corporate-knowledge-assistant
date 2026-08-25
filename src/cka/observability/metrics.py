from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    registry=REGISTRY,
)

RAG_RETRIEVAL_DURATION_SECONDS = Histogram(
    "rag_retrieval_duration_seconds", "Retrieval stage duration in seconds", registry=REGISTRY
)

RAG_RERANKING_DURATION_SECONDS = Histogram(
    "rag_reranking_duration_seconds", "Reranking stage duration in seconds", registry=REGISTRY
)

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total", "Total LLM generation calls", ["provider"], registry=REGISTRY
)

# Note: the roadmap also lists prompt_injection_detected_total. Not added
# here — ADR-009 deliberately rejects keyword/pattern-based injection
# "detection" (false positives, false sense of security; the real defense is
# structural isolation, see application/rag/prompt_builder.py), so there is
# no real signal to drive this counter honestly. Revisit if a genuine
# detection signal (e.g. anomalous query-volume patterns) is implemented.


def render_latest() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
