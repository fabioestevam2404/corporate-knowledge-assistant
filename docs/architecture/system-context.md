# System Context

Who/what talks to the Corporate Knowledge Assistant, at the highest level
(C4 "System Context" view) — real actors and external systems, not
hypothetical ones.

```
                    ┌─────────────────────┐
                    │   Employee /         │
                    │   Manager / Admin     │
                    │   (real JWT roles)    │
                    └──────────┬────────────┘
                               │ HTTPS (ALB in
                               │ deployed envs;
                               │ plain HTTP on
                               │ localhost:8010
                               │ in local dev)
                               ▼
                    ┌─────────────────────────┐
                    │  Corporate Knowledge     │
                    │  Assistant (this system) │
                    └───┬───────┬──────────┬───┘
                        │       │          │
          ┌─────────────┘       │          └─────────────┐
          ▼                     ▼                         ▼
┌───────────────────┐ ┌──────────────────┐   ┌─────────────────────┐
│ PostgreSQL +        │ │ Anthropic API     │   │ OpenTelemetry        │
│ pgvector             │ │ (claude-sonnet-5)  │   │ Collector → Jaeger    │
│ (documents, chunks,  │ │ real generation +  │   │ Prometheus scrapes    │
│ users, embeddings)   │ │ LLM-as-judge eval   │   │ /metrics → Grafana    │
└───────────────────┘ └──────────────────┘   └─────────────────────┘
```

## Real actors

- **Employee / Manager / Admin**: three real roles (`domain/user.py`),
  authenticated via `POST /auth/login`, authorized per-request via JWT +
  RBAC (`require_permission`) + a real per-user `AccessScope` that filters
  which document sources are visible at retrieval time.

## Real external systems

- **PostgreSQL 16 + pgvector**: system of record for documents, chunks
  (with embeddings), users, and access-control metadata. Not swappable
  without a real migration (embedding dimension is pinned to 384 in the
  schema).
- **Anthropic API**: real generation (`claude-sonnet-5`) and real
  LLM-as-judge evaluation (faithfulness/answer relevance). Optional in the
  sense that the system degrades to `FakeLLMProvider` without a key — not
  optional in the sense that no environment beyond local dev should run
  without it (see `.env.production.example`, which requires it with no
  default).
- **Jaeger / Prometheus / Grafana**: observability sinks, not
  dependencies the request path blocks on — tracing/metrics export is
  fire-and-forget from the app's perspective.

## What is explicitly out of scope

No external identity provider (SSO/OIDC) — users are managed directly in
this system's own `users` table. No external document-ingestion source
(SharePoint, Confluence, etc.) — documents are ingested via `POST
/documents` against sources pre-approved in
`data/sources/registry.yaml`. Both are real, deliberate scope boundaries,
not gaps discovered late.
