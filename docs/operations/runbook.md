# Runbook

Real operational procedures, using real commands already verified against
this repository across Blocks 1–4.

## Starting the stack (local dev)

```
docker compose up -d
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/health/ready
```
Real host ports (non-default on this dev machine — see
`docs/release-gate/PROGRESS.md`): api `8010`, db `5434`, jaeger UI `16686`,
prometheus `9090`, grafana `3000`.

## Seeding a test user

```
uv run python scripts/seed_users.py
```
Prints a real, randomly-generated password once per role
(EMPLOYEE/MANAGER/ADMIN) — never stored, never logged again. Re-running is
safe (existing usernames are skipped, not reset).

## Running the smoke test

```
BASE_URL=http://127.0.0.1:8010 SMOKE_USERNAME=<user> SMOKE_PASSWORD=<pw> \
  bash scripts/smoke_test.sh
```
Exercises `/health` → `/health/ready` → `/auth/login` → `/retrieve` →
`/ask` in sequence against a live stack (local, staging, or production via
`BASE_URL`). Exits non-zero with the real HTTP status/body on first
failure.

## Running database migrations

```
uv run alembic upgrade head
```
Real check: `psql -h localhost -p 5434 -U cka -d cka -c '\d documents'` to
confirm the schema landed.

## Running the full test suite

```
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests scripts
uv run pytest tests/unit tests/integration tests/security tests/observability \
  --cov=src/cka --cov-report=term-missing
```
Integration/security/observability tests need the real `db`/`jaeger`
containers up (`docker compose up -d db jaeger`) — they are not mocked.

## Running the evaluation gate

```
uv run python scripts/evaluate.py
```
Real exit code 0/non-zero based on real thresholds
(`Settings.evaluation_min_*`). See `docs/evaluation/evaluation.md`.

## Deploying a new version (once real cloud infra exists — see ADR-013)

1. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z` (triggers `release.yml`
   in real CI — see ADR-012 for why this is written but not yet
   runner-verified on this project).
2. `release.yml` builds, tags, and pushes to GHCR.
3. `terraform apply` in the relevant `infra/environments/{staging,production}`
   directory with `container_image` pointing at the new tag (never
   `apply`'d in this exercise — see `infra/README.md`).
4. Run `scripts/smoke_test.sh` against the real deployed `BASE_URL`
   before considering the deploy complete.

## Rotating secrets

`JWT_SECRET_KEY` rotation invalidates all outstanding tokens immediately
(stateless JWT — no revocation list exists). `ANTHROPIC_API_KEY` and
`GRAFANA_ADMIN_PASSWORD` rotate independently, no coordination required.
In the Terraform scaffolding, all three are SSM `SecureString` parameters
(`infra/modules/application`) — update the parameter, then force a new ECS
deployment to pick it up.
