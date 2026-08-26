# Corporate Knowledge Assistant

An enterprise RAG (Retrieval-Augmented Generation) system: authenticated,
role- and document-ACL-aware question answering over a governed corporate
document corpus, with citations, abstention on insufficient evidence, and
full observability/auditability.

**Status: `v1.0.0`.** Built incrementally across four blocks, each closed
out with real command output, not aspirational checkmarks — the full,
block-by-block evidence log lives in
[`docs/release-gate/PROGRESS.md`](docs/release-gate/PROGRESS.md), and the
consolidated release decision is in
[`docs/release-gate/RELEASE_GATE_v1.0.0.md`](docs/release-gate/RELEASE_GATE_v1.0.0.md).

That release gate document is deliberately honest, including where it
isn't clean: one real evaluation-quality check
(`citation_accuracy`) currently fails against the golden dataset, for a
specific, understood, documented reason — and that failure was left in
place rather than resolved by loosening a threshold, because doing so
would have quietly weakened the system's real hallucination-prevention
guarantee. Several other real defects were found and fixed the same way,
at every stage of the project, right up through configuring a real
`ANTHROPIC_API_KEY` for the first time post-tag. That trail is the point:
every claim in this repository is backed by something that was actually
run, not just written down.

## What's implemented

- FastAPI + PostgreSQL/pgvector, structured observability (structlog with
  request correlation), a governed Source Registry gating document
  ingestion.
- Chunking + real sentence-transformer embeddings, hybrid retrieval
  (pgvector cosine + PostgreSQL full-text search, RRF-fused) with
  cross-encoder reranking.
- A grounded RAG orchestrator (`POST /ask`) with citation validation,
  rule-based confidence, and abstention on insufficient evidence — real
  generation via Anthropic Claude behind an abstract `LLMProvider`
  (`FakeLLMProvider` fallback when no key is configured).
- JWT authentication + Argon2id password hashing, RBAC + real per-role
  document ACL (the roadmap's flagship EMPLOYEE-vs-MANAGEMENT
  authorization test is real and passing), per-user rate limiting.
- A RAG evaluation framework with a real Golden Dataset
  (`scripts/evaluate.py`) and real LLM-as-judge scoring.
- Real distributed tracing (OpenTelemetry → Jaeger) and metrics
  (Prometheus → Grafana, both file-provisioned, not clicked together).
- Multi-stage, non-root Docker build; 4 GitHub Actions workflows
  (CI, security scanning, container build/scan, tag-triggered release);
  AWS Terraform scaffolding for staging/production (`infra/`).
- A full documentation set — architecture, API reference, security
  controls, evaluation methodology, operations runbook — in
  [`docs/`](docs/), and 15 real ADRs in [`docs/adr/`](docs/adr/).

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
tests (`tests/observability`) require `docker compose up -d db` first, and
run against a dedicated `cka_test` database (never the one real dev/demo
data lives in — see `tests/conftest.py`).

## Evaluation

```bash
uv run python scripts/evaluate.py
```

Runs the real Golden Dataset (`data/evaluation/`) against the real retriever
and RAG orchestrator, writes `reports/evaluation_latest.{json,md}`, and exits
non-zero if the quality gate (`Settings.evaluation_min_*`) is violated. See
[`docs/evaluation/`](docs/evaluation/) for methodology and the real,
current results — including the one honestly-failing check.

## Deployment

`infra/` holds real, structurally-correct Terraform (AWS: VPC, RDS/pgvector,
ECS Fargate, ALB) for `staging`/`production` — written and reviewable, never
applied (no cloud account backs this project; see
[`docs/adr/ADR-013-production-deployment-and-release-engineering.md`](docs/adr/ADR-013-production-deployment-and-release-engineering.md)
and [`infra/README.md`](infra/README.md) for exactly what that does and
doesn't mean).

## Architecture decisions

See [`docs/adr/`](docs/adr/) for the 15 Architecture Decision Records
governing this project — source governance, database choice, layered
architecture, framework choice, security hardening, evaluation,
observability, CI/CD, deployment, and documentation governance.
