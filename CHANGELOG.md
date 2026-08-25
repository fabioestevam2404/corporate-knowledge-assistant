# Changelog

Generated from this repository's real `git log` (`git log --pretty=format:"%H|%ad|%s" --date=short`).
Two commits exist because Blocks 1–3 were developed and validated before a
git history strategy was decided for this exercise — confirmed with the
user and documented honestly rather than fabricating intermediate commits
that never happened. See `docs/release-gate/PROGRESS.md` for the real,
block-by-block evidence behind each commit.

## [Unreleased]

## 2026-08-25

- `18f769c` — **Block 4 (Sprints 12–14): CI/CD, deployment IaC, and
  documentation.** Multi-stage non-root Dockerfile, 4 GitHub Actions
  workflows, `pip-audit`/`semgrep`/`gitleaks` run for real. Two real
  production defects found and fixed: a `PermissionError` from `/app`
  staying root-owned under the non-root user, and an orphaned `hf_xet`
  subprocess going zombie with no init process to reap it (fixed with
  `init: true`/`tini`) — the latter escalated to a stuck WSL2 VM requiring
  a full Windows restart. AWS Terraform scaffolding (never applied — no
  cloud account). Real `scripts/smoke_test.sh`, verified end-to-end.
  Architecture/API/security/evaluation/operations/governance documentation
  written from the real codebase. ADR-012, ADR-013, ADR-014.

- `46d9829` — **Blocks 1–3: Foundation, RAG core, and
  security/evaluation/observability.** Squashed commit — see
  `docs/release-gate/PROGRESS.md` for the real, incremental evidence this
  represents (it was not committed incrementally at the time; the git
  history strategy for this exercise was decided after Blocks 1–3 were
  already built and validated). Covers: layered architecture, FastAPI +
  PostgreSQL/pgvector, hybrid retrieval + reranking + Anthropic generation,
  JWT auth + RBAC + document-level `AccessScope` (with the roadmap's
  headline EMPLOYEE-vs-MANAGEMENT ACL test passing for real), Golden
  Dataset evaluation gate, real OpenTelemetry tracing + Prometheus metrics
  + Grafana dashboard.
