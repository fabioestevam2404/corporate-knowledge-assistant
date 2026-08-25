# API Reference

Every endpoint below is real — extracted directly from
`src/cka/api/routes/*.py` and `src/cka/main.py`, request/response shapes
copied from the actual Pydantic models, not hand-written approximations.
Base path is unprefixed (no `/api/v1` etc.) — all routes are mounted at the
application root.

## Authentication

All endpoints except `GET /`, `GET /health*`, `POST /auth/login`, and
`GET /metrics` require a JWT bearer token:

```
Authorization: Bearer <access_token>
```

Obtained from `POST /auth/login`. Tokens expire after
`Settings.access_token_expire_minutes` (default 30 minutes).

---

## `GET /`

Liveness/identity check. No auth required.

**Response 200**
```json
{"message": "Corporate Knowledge Assistant API", "status": "running"}
```

## `GET /health`

Basic health check. No auth required.

**Response 200**
```json
{"status": "healthy", "service": "corporate-knowledge-assistant"}
```

## `GET /health/live`

Liveness probe (process is up, does not check dependencies). No auth
required.

## `GET /health/ready`

Readiness probe — checks the real database connection
(`connect_args={"connect_timeout": 3}`, see ADR / Block 1 defect fix). No
auth required.

**Response 200**
```json
{"status": "ready"}
```

---

## `POST /auth/login`

**Request**
```json
{"username": "string", "password": "string"}
```

**Response 200**
```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

**Response 401** — invalid credentials. Timing-normalized against
username-enumeration (real Argon2id verification runs even for unknown
usernames — see Block 3 defect fix in `PROGRESS.md`).

---

## `POST /retrieve`

Requires a valid bearer token. Results are filtered by the caller's real
`AccessScope` (RBAC + document ACL) — never returns chunks the caller isn't
authorized to see, regardless of query relevance.

**Request**
```json
{"query": "string", "top_k": 5}
```
`top_k`: integer, `1 <= top_k <= 20`, default `5`.

**Response 200**
```json
{
  "query": "string",
  "results": [
    {
      "chunk_id": "string",
      "document_id": "string",
      "source_id": "string",
      "content": "string",
      "page_number": 1,
      "chunk_index": 0,
      "score": 0.87
    }
  ]
}
```
`score` is the fused hybrid-retrieval score (pgvector cosine + full-text
search, combined via Reciprocal Rank Fusion, `k=60`) after cross-encoder
reranking.

---

## `POST /ask`

Requires a valid bearer token. Runs the full RAG pipeline: hybrid retrieval
→ reranking → context building → LLM generation → citation validation.
Results are filtered by the same `AccessScope` as `/retrieve` before ever
reaching the LLM — an unauthorized source is never included in context, not
just redacted after generation.

**Request**
```json
{"query": "string"}
```
`query`: 1 to `Settings.max_query_length` characters (default 2000) — longer
requests get `400`.

**Response 200**
```json
{
  "answer": "string",
  "sources": [
    {"document_id": "string", "page_number": 1, "chunk_id": "string"}
  ],
  "confidence": "low | medium | high",
  "grounded": true,
  "trace_id": "string"
}
```
`trace_id` is the real OpenTelemetry trace id (see ADR-011), queryable
directly against Jaeger's own API. Without `ANTHROPIC_API_KEY` configured,
`answer` is a fixed fallback string
(`"ANTHROPIC_API_KEY not configured — no real answer available."`),
`grounded: false`, `sources: []` — see
`docs/governance/model-governance.md`.

**Response 429** — rate limit exceeded (`Settings.rate_limit_per_minute`,
default 60/minute, per user).

---

## `POST /documents`

`multipart/form-data`. Requires `documents:write` permission (MANAGER/ADMIN
roles — see RBAC in `docs/security/threat-model.md`).

**Request** (form fields)
- `source_id`: string — must reference an approved entry in
  `data/sources/registry.yaml`.
- `file`: the document file (PDF or plain text).

**Response 201**
```json
{"document_id": "string", "filename": "string", "chunk_count": 12}
```

**Response 400** — unknown or unapproved `source_id`.

## `DELETE /documents/{document_id}`

Requires `documents:delete` permission (ADMIN role only).

**Response 204** — no body.

**Response 404** — document does not exist.

---

## `GET /metrics`

Prometheus exposition format. No auth required (matches Prometheus's own
scrape model — not intended to be internet-facing directly; restrict at the
network layer, e.g. the ALB security group in `infra/modules/networking`
does not expose this port publicly beyond the app tier).

Real metrics exposed: `http_requests_total`,
`http_request_duration_seconds`, `rag_retrieval_duration_seconds`,
`rag_reranking_duration_seconds`, `llm_requests_total` — see ADR-011.

---

## Error shape

All errors (validation, auth, not-found, rate-limit, unhandled) return:
```json
{"detail": "string"}
```
or, for FastAPI validation errors (422):
```json
{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": "..."}]}
```
Unhandled exceptions are caught by a global handler
(`src/cka/api/errors.py`) and never leak a stack trace to the client — logged
structurally instead (`request_id` correlates the two).
