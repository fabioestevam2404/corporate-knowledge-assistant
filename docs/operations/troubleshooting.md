# Troubleshooting

Real incidents encountered and resolved while building/validating this
project (Blocks 1–4), kept here because each one is a genuine, non-obvious
operational lesson — not a hypothetical FAQ.

## `/health/ready` hangs instead of failing fast

**Symptom**: a request to `/health/ready` never returns when PostgreSQL is
unreachable.

**Root cause** (Block 1, real defect): `make_engine()` originally had no
`connect_timeout`, so SQLAlchemy's default TCP timeout applied — a
21-minute real hang was measured against an unreachable database.

**Fix**: `connect_args={"connect_timeout": 3}` in
`infrastructure/database/connection.py`. If this regresses, check that
argument is still present before debugging anything else.

## `ForeignKeyViolation` inserting a document + its chunks

**Symptom**: `POST /documents` (or a test seeding a document) fails with a
foreign-key violation on the chunks table.

**Root cause** (Block 2, recurred in Block 3 production code):
`DocumentModel`/`ChunkModel` have no ORM `relationship()`, so SQLAlchemy
can't infer insert order — the document row isn't flushed before chunks
referencing it are inserted.

**Fix**: `SqlAlchemyDocumentRepository.save()` flushes internally after
`session.merge(model)` — this is fixed at the root as of Block 3;
`session.flush()` should never need to be added manually at a call site
again. If this recurs, check whether a *new* repository method was added
that bypasses `.save()`.

## `PermissionError: [Errno 13] Permission denied: '/app/.cache'`

**Symptom**: first real `/retrieve` or `/ask` call against the non-root
image fails with this traceback.

**Root cause** (Block 4): `/app` stayed root-owned even after
`COPY --chown=app:app` copied specific subdirectories into it — `app`
couldn't `mkdir /app/.cache` for the HuggingFace model cache.

**Fix**: `RUN mkdir -p /app/.cache && chown -R app:app /app/.cache` before
`USER app` in the Dockerfile. Already fixed — if a similar error appears
for a *different* path, the same pattern (a directory `app` needs to write
to, created only by `COPY --chown` of its *contents*, not itself) is the
likely cause.

## A container becomes unkillable (`docker kill`/`docker rm -f` hang)

**Symptom**: `docker kill`/`docker rm -f` hang indefinitely against one
specific container; `docker ps`/`docker info` remain responsive.

**Root cause** (Block 4, the most significant real incident this project
surfaced): a native subprocess spawned during a dependency download
(`hf_xet`, used by `sentence-transformers`/`huggingface_hub`) was orphaned
by a transient DNS failure. Without an init process as PID 1, the orphan
went zombie and was never reaped — `docker restart` failed outright with
`container ... is zombie and can not be killed`. Left unresolved, this
escalated: the zombie wedged the WSL2 VM itself (`vmmemWSL`) badly enough
that Docker Desktop's backend couldn't restart
(`engine linux/wsl failed to start: ... wsl.exe -l -v --all` timing out),
and killing `vmmemWSL`/`wslservice` directly required admin privileges.
**A full Windows restart was required to recover.**

**Fix**: `init: true` on the `api` service in `docker-compose.yml` — runs
`tini` as PID 1 instead of `uvicorn` directly, so orphaned subprocesses get
reaped instead of going zombie. Verified: `docker inspect ... {{.HostConfig.Init}}`
→ `true`.

**If this happens again despite the fix**: don't spend more than a few
minutes retrying `docker kill`/`rm -f` — if the container's own
`docker info`/`docker ps` still work but that one container won't die,
suspect the WSL2 VM is already wedged underneath it, and a full restart
(Windows, or `wsl --shutdown` from an **elevated** terminal — a
non-elevated one will get `Access denied` trying to kill `vmmemWSL`) is
the fastest real path to recovery, not further retries.

## A live `docker stats`/`docker kill` call itself times out

**Symptom**: `docker stats`/`docker kill` against a specific container
takes far longer than normal (many seconds to tens of minutes), while
`docker ps`/`docker info` return quickly.

**Root cause** (Block 4, SBOM generation): a resource-heavy container
(Syft cataloging an 8GB+ image) starving the daemon's ability to service
other requests promptly — not necessarily a zombie, just contention.
Distinguish from the zombie case above by checking `docker stats` for the
suspect container: real, growing CPU/memory/block-I/O means it's genuinely
working, not stuck.

**If it becomes genuinely unresponsive** (as eventually happened in this
exact incident — see `docs/release-gate/PROGRESS.md`, Sprint 12), treat it
as the zombie case above rather than waiting indefinitely.

## `docker compose stop` reports "did not receive an exit event"

**Symptom**: `docker compose stop <service>` errors with
`tried to kill container, but did not receive an exit event`, even though
the application's own logs show a clean shutdown sequence
(`INFO: Shutting down` → `Application shutdown complete`).

**Root cause** (Block 4): application-level graceful shutdown is real and
working (`uvicorn` correctly handles `SIGTERM`, forwarded by `tini`) — this
error is a daemon-level event-delivery failure, most likely caused by the
same host Docker/WSL2 resource contention documented above (a stuck
container elsewhere competing for daemon attention).

**Distinguish from a real app bug**: check the container's own logs first
— if they show the clean shutdown sequence, the application is fine; the
daemon failed to notice. Don't chase this as an application defect.

## `/ask` returns a fixed fallback string instead of a real answer

**Symptom**: `{"answer":"ANTHROPIC_API_KEY not configured — no real answer
available.","grounded":false}`.

**Not a bug** — this is `FakeLLMProvider`'s documented behavior when
`ANTHROPIC_API_KEY` is unset. See `docs/governance/model-governance.md`.
