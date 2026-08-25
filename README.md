# Corporate Knowledge Assistant

An enterprise RAG (Retrieval-Augmented Generation) system: authenticated,
role- and document-ACL-aware question answering over a governed corporate
document corpus, with citations, abstention on insufficient evidence, and
full observability/auditability.

This repository is being built incrementally, in blocks, against the
technical specification in `../Corporate_Knowledge_Assistant_COMPLETO.md`
(a 15-sprint conceptual roadmap). Real progress — with real test evidence,
not aspirational checkmarks — is tracked in
[`docs/release-gate/PROGRESS.md`](docs/release-gate/PROGRESS.md).

## Status: Block 3 — Security, Evaluation, Observability (Sprints 09–11)

Implemented so far: FastAPI skeleton, Docker + PostgreSQL/pgvector, structured
observability (structlog + request correlation), a governed Source Registry
with document ingestion, chunking + real embeddings, hybrid retrieval
(vector + PostgreSQL full-text search, RRF-fused) with cross-encoder
reranking, and a grounded RAG orchestrator (`POST /ask`) with citation
validation, rule-based confidence, and abstention. LLM: Anthropic Claude
behind an abstract `LLMProvider`. On top of that, this block adds: JWT
authentication + Argon2id password hashing, RBAC + real per-role document
ACL (the roadmap's flagship EMPLOYEE-vs-MANAGEMENT authorization test is
real and passing), per-user rate limiting, a RAG evaluation framework with a
real Golden Dataset (`scripts/evaluate.py`), and real distributed tracing
(OpenTelemetry → Jaeger) + metrics (Prometheus → Grafana, both
file-provisioned).

## Quick start

```bash
# 1. Install dependencies (uv manages its own Python 3.12)
pip install uv
uv python install 3.12
uv sync

# 2. Start PostgreSQL + pgvector
docker compose up -d db

# 3. Apply migrations
cp .env.example .env
uv run alembic upgrade head

# (optional) add a real ANTHROPIC_API_KEY to .env for real /ask generation —
# without it, /ask still works (retrieval, ACL, abstention), using
# FakeLLMProvider instead of a real model call.

# 4. Seed a user (see scripts/seed_users.py) and log in
uv run python scripts/seed_users.py
curl -X POST http://127.0.0.1:8000/auth/login -d '{"username": "employee.test", "password": "..."}'

# 5. Run the API
uv run uvicorn cka.main:app --reload

# 6. Check it's alive, then ask something (with the token from step 4)
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer <token>" -d '{"query": "your question here"}'
```

> Running the full stack via `docker compose up` instead of `uvicorn`
> directly? The API is published on host port `8010` (not 8000), Postgres on
> `5434` (not 5432), Jaeger UI on `16686`, Prometheus on `9090`, Grafana on
> `3000` — see the port note in `docs/release-gate/PROGRESS.md` for why the
> app ports are non-default.

## Tests

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests scripts
uv run pytest --cov=src/cka --cov-report=term-missing
```

Unit tests (`tests/unit`) run without Docker. Integration tests
(`tests/integration`), security tests (`tests/security`) and observability
tests (`tests/observability`) require `docker compose up -d db` first.

## Evaluation

```bash
uv run python scripts/evaluate.py
```

Runs the real Golden Dataset (`data/evaluation/`) against the real retriever
and RAG orchestrator, writes `reports/evaluation_latest.{json,md}`, and exits
non-zero if the quality gate (`Settings.evaluation_min_*`) is violated.

## Architecture decisions

See [`docs/adr/`](docs/adr/) for the Architecture Decision Records governing
this project (source governance, database choice, layered architecture,
framework choice, security hardening, evaluation, observability, and more as
later blocks land).
