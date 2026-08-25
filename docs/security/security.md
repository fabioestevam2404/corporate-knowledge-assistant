# Security Controls

Complements `threat-model.md` (STRIDE analysis, AI-specific threats, the
headline ACL test) with a practical reference of what's actually
implemented — every control below is real code or a real, run tool, cross-
referenced to its source.

## Authentication & session

- **Password hashing**: Argon2id (`argon2-cffi`), real, not a placeholder —
  `infrastructure/security/password_hashing.py`.
- **Timing-attack resistance**: login always runs a real Argon2id
  verification, even for unknown usernames (against a real dummy hash),
  normalizing response time — a real defect found and fixed in Block 3
  (`_DUMMY_HASH` in `application/authenticate_user.py`).
- **Tokens**: JWT (PyJWT, HS256), `Settings.access_token_expire_minutes`
  (default 30 min). `JWT_SECRET_KEY` has a hard runtime failure if left at
  its dev-only default when `ENVIRONMENT=production`
  (`Settings._forbid_dev_jwt_secret_in_production`) — enforced in code, not
  just documentation.

## Authorization

- **RBAC**: `require_permission(...)` dependency, three real roles
  (EMPLOYEE/MANAGER/ADMIN, `domain/user.py`).
- **Document-level ACL**: `AccessScope`, applied inside the retrieval query
  itself (see `docs/architecture/data-flow.md`) — never a post-hoc filter.
  Verified by the headline test in `threat-model.md` §"Teste crítico de
  autorização".

## Rate limiting

In-memory sliding window (`infrastructure/security/rate_limiting.py`),
`Settings.rate_limit_per_minute` (default 60/min), per authenticated user.
Real 429 responses verified in `tests/security/test_rate_limiting.py`.

## Prompt-injection defense

Context isolation in `application/rag/prompt_builder.py` — retrieved
document content is wrapped in `<UNTRUSTED_DOCUMENTS>`, explicitly
instructed (in `SYSTEM_PROMPT`) to never be treated as instructions.
Real adversarial document ingested and tested against in
`tests/security/test_prompt_injection.py` — not a synthetic unit test of
the prompt string alone.

## Input validation

- SQL injection: parameterized queries throughout (SQLAlchemy Core/ORM,
  never string-formatted SQL) — probed for real in
  `tests/security/test_sql_injection.py`.
- Query length limits (`Settings.max_query_length`), `top_k` bounds
  (`1 <= top_k <= 20`) enforced by Pydantic field constraints, not
  hand-written checks.

## Secrets handling

- Never in the image: `.dockerignore` excludes `.env`; verified by
  `tests/security/test_secrets.py`.
- Never in plaintext in deployed infrastructure: SSM Parameter Store
  `SecureString` in the Terraform scaffolding (`infra/modules/application`,
  ADR-013) — same rule extended from image to deployment.
- Never in source history unreviewed: `gitleaks` with a baseline mechanism
  for the one real historical finding this project actually had, reviewed
  and fixed at the root (ADR-012) — not silently allowlisted.

## Supply chain & container hardening (Block 4 / ADR-012)

| Control | Tool | Real result |
|---|---|---|
| Dependency vulnerabilities | `pip-audit` | 0 known vulnerabilities |
| SAST | `semgrep --config auto` | 290 rules, 89 files, 0 findings |
| Secret scanning | `gitleaks` (baseline) | 0 leaks (1 historical finding reviewed, fixed at the root) |
| Non-root container | multi-stage Dockerfile, `USER app` (uid 999) | verified via `docker run ... id` |
| No build toolchain in final image | multi-stage build | `builder` stage discarded, only `.venv`/`src`/`migrations`/`data` copied |
| Container SBOM | Syft (`docker.yml` in CI) | documented local-environment gap, see PROGRESS.md — runs correctly in CI |
| Container CVE scan | Trivy (`docker.yml` in CI) | not run locally in this exercise — CI-only, same reasoning as SBOM |

## Observability without data leakage

No document content, full prompt text, or raw query text appears in span
attributes, metric labels, or log fields — only identifiers, counts, and
durations. Tested explicitly with a real marker string
(`tests/observability/test_no_sensitive_data_in_telemetry.py`) — verifies
the marker never appears in logs or `/metrics`, not just an assertion about
intent.

## Known gaps (see `threat-model.md` for the full list)

No persistent `GET /audit` endpoint (structured log events only), no
`prompt_injection_detected_total` metric (no real detection signal exists
to drive it honestly — ADR-009 rejects keyword-based fake detection). Both
carried forward from Block 3, unchanged in Block 4.
