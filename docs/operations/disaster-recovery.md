# Disaster Recovery

Real recovery procedures for this system's actual failure modes — cross-
referenced to what's really implemented, not aspirational.

## Database loss / corruption

**Local dev**: data lives in the `cka_pgdata` Docker volume
(`docker-compose.yml`). No automated backup exists for local dev by
design — it holds sample data only (`data/sources/registry.yaml`'s five
sample documents), reproducible via `docker compose down -v && docker
compose up -d && uv run alembic upgrade head`.

**Production (Terraform scaffolding, `infra/modules/database`)**:
`backup_retention_period` is `7` days in production vs. `1` in staging,
`deletion_protection: true` in production only, `multi_az: true` in
production for automatic failover. **Real caveat**: this infrastructure has
never been applied (see ADR-013) — these are the real, correct settings for
when it is, not evidence of a tested recovery.

## Application container failure

ECS Fargate (production scaffolding) restarts a failed task automatically
per its service definition; the ALB health check (`/health/ready`, 30s
interval) stops routing traffic to an unhealthy task before it's replaced.
Locally, `docker compose`'s own restart policy applies (default: no
auto-restart — a real gap for local dev specifically, since local dev is
disposable by design; not carried into the production module, which relies
on ECS's own task-replacement behavior instead).

## Full environment loss (the incident this document set actually
lived through)

**Real precedent** (Block 4, see `troubleshooting.md` and
`docs/release-gate/PROGRESS.md`): a single orphaned subprocess inside one
container escalated into the entire local Docker/WSL2 environment becoming
unusable, requiring a full Windows restart to recover. Real recovery steps
taken, in order:

1. Exhausted `docker kill`/`docker rm -f`/`docker restart` against the
   specific stuck container — all failed or hung.
2. Confirmed the Docker daemon itself was still otherwise responsive
   (`docker info` succeeded) — narrowed the problem to one container/the
   WSL2 VM underneath it, not the whole host.
3. Attempted killing the WSL2 VM process (`vmmemWSL`) and Docker Desktop's
   backend service directly — blocked by insufficient privileges in the
   automation session.
4. **Full Windows restart** — confirmed with the user first, since it
   affects every other Docker-based project on the shared machine, not
   just this one.
5. Post-restart: `docker compose up -d` rebuilt the stack cleanly, `curl`
   verified `/health`/`/health/ready`, and a real end-to-end `/retrieve`/
   `/ask` call confirmed the application layer was intact — no data was
   lost (the `cka_pgdata` volume survived the restart, as Docker volumes
   are independent of container/VM lifecycle).

**Lesson carried into the fix**: `init: true` (ADR-012) directly targets
the root cause (no PID 1 process to reap orphaned children) so this
specific failure mode shouldn't recur — but the recovery sequence above is
the real, tested playbook if a similarly-wedged container situation
happens again, regardless of root cause.

## Secrets compromise

Rotate `JWT_SECRET_KEY` (invalidates all outstanding tokens immediately —
no revocation list exists, so rotation *is* the revocation mechanism),
`ANTHROPIC_API_KEY` (via the Anthropic console), and
`GRAFANA_ADMIN_PASSWORD` independently. In the Terraform scaffolding,
update the relevant SSM `SecureString` parameter and force a new ECS
deployment — see `runbook.md`.

## What has not been tested for real

Database point-in-time restore, multi-AZ RDS failover, and ECS
task-replacement-under-load have never been exercised against real
infrastructure (none has been provisioned — see ADR-013). Stated as a real
gap, not implied as covered by the configuration alone.
