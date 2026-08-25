# Architecture

Real architecture of the system as implemented — cross-checked against
`src/cka/` directly, not copied from the roadmap's original proposal (which
this document supersedes wherever the two differ; deviations are called out
explicitly in each block's section of `docs/release-gate/PROGRESS.md`).

## Layering

```
src/cka/
├── api/            FastAPI routes, request/response models, DI wiring
├── application/     use cases (AuthenticateUser, IngestDocument,
│                     ProcessDocument, DeleteDocument, RagOrchestrator, ...)
├── domain/          entities, value objects, domain exceptions —
│                     no framework or infrastructure imports
├── infrastructure/   real implementations of domain-defined interfaces:
│   ├── database/       SQLAlchemy models/repositories, Alembic migrations
│   ├── embeddings/      sentence-transformers embedding service
│   ├── ranking/         cross-encoder reranker
│   ├── retrieval/       hybrid retrieval (pgvector + full-text, RRF)
│   ├── processing/      chunking, PDF/text loaders
│   ├── llm/              Anthropic provider, LLM-as-judge, fake fallback
│   ├── security/         Argon2id hashing, JWT, rate limiting
│   └── sources/          source registry (data/sources/registry.yaml)
├── core/             Settings (pydantic-settings), app wiring
└── observability/    structlog config, OpenTelemetry tracing helpers
```

Dependency direction is strictly inward: `api → application → domain`, and
`infrastructure` implements interfaces `domain`/`application` define —
`domain` never imports from `infrastructure` or `api`. Verified structurally
by the fact that `domain/` has zero third-party imports beyond the standard
library (no SQLAlchemy, no FastAPI, no `sentence_transformers` anywhere
under `domain/`).

## Request lifecycle (real, `POST /ask`)

1. **API layer** (`api/routes/ask.py`): validates `AskRequest`, resolves DI
   dependencies (`AskKnowledgeBaseDep`, `AccessScopeDep`, `RateLimitDep`).
2. **Application layer** (`application/rag/orchestrator.py`): coordinates
   the pipeline — never talks to Postgres or the LLM API directly, only
   through injected interfaces.
3. **Infrastructure layer**: hybrid retrieval (`infrastructure/retrieval/`)
   → cross-encoder reranking (`infrastructure/ranking/`) → context building
   (`application/rag/prompt_builder.py`) → real Anthropic call
   (`infrastructure/llm/anthropic_provider.py`, or `FakeLLMProvider` if no
   key) → citation validation.
4. Every stage emits a real OpenTelemetry span (see ADR-011) and a
   structured log line — the same request is traceable through Jaeger,
   Prometheus, and `docker compose logs` using the same `trace_id`.

See `data-flow.md` for the full diagram.

## Cross-cutting concerns

- **Security** (ADR-009): JWT auth, RBAC (`require_permission`), per-user
  document `AccessScope` enforced at the retrieval layer — never as a
  post-hoc filter on the LLM's answer.
- **Observability** (ADR-011): structured logging (Block 1) +
  OpenTelemetry tracing + Prometheus metrics (Block 3), all real, none
  simulated.
- **Evaluation** (ADR-010): `scripts/evaluate.py` runs the Golden Dataset
  against the real pipeline, gates on real thresholds
  (`Settings.evaluation_min_*`).

## What this document does not claim

No component here has been deployed to a real cloud environment — see
`infra/README.md` and ADR-013. Every diagram/description in this document
set reflects the system as it runs locally via `docker-compose.yml`,
verified with real commands throughout `docs/release-gate/PROGRESS.md`.
