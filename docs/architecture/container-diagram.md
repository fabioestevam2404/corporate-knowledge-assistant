# Container Diagram

Real deployable units (C4 "Container" view) — one entry per real service in
`docker-compose.yml`, with real ports as actually configured (host ports are
intentionally non-default on this dev machine — see the note at the top of
`docs/release-gate/PROGRESS.md`).

```
┌──────────────────────────────────────────────────────────────────────┐
│                      docker-compose.yml (local dev)                   │
│                                                                         │
│  ┌────────────┐  8010:8000  ┌─────────────┐                          │
│  │   client    │────────────▶│    api      │  Dockerfile (multi-stage,│
│  │ (curl/UI)   │             │ (uvicorn,    │  non-root, init:true —   │
│  └────────────┘              │  FastAPI)    │  see ADR-012)             │
│                               └──┬───┬───┬──┘                          │
│                                  │   │   │                              │
│                     5434:5432    │   │   │  4317 (OTLP gRPC)            │
│                    ┌─────────────┘   │   └──────────────┐               │
│                    ▼                 │                  ▼               │
│           ┌────────────────┐         │        ┌──────────────────┐     │
│           │  db (Postgres   │        │        │  jaeger            │     │
│           │  16 + pgvector) │        │        │  (16686 UI)         │     │
│           └────────────────┘         │        └──────────────────┘     │
│                                        │                                 │
│                                        ▼ (scraped, not pushed)           │
│                              ┌──────────────────┐   3000:3000            │
│                              │  prometheus        │──────────┐           │
│                              │  (9090)             │          ▼           │
│                              └──────────────────┘   ┌──────────────────┐ │
│                                                       │  grafana           │ │
│                                                       │  (anonymous Viewer, │ │
│                                                       │  see ADR-012 fix)   │ │
│                                                       └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

## Real containers

| Service | Image | Host port | Real role |
|---|---|---|---|
| `api` | built from local `Dockerfile` | `8010` | FastAPI app (this system) |
| `db` | `pgvector/pgvector:pg16` | `5434` | System of record |
| `jaeger` | `jaegertracing/all-in-one:1.60` | `16686` (UI), `4317` (OTLP) | Trace storage/UI |
| `prometheus` | `prom/prometheus:v2.55.1` | `9090` | Metrics scrape/storage |
| `grafana` | `grafana/grafana:11.2.0` | `3000` | Metrics dashboard (file-provisioned) |

## Production topology (Terraform scaffolding — not deployed, see ADR-013)

`infra/modules/application` replaces the single `api` container with an ECS
Fargate service behind an ALB (public subnet), talking to `db`'s production
equivalent (RDS, private subnet) and the same real Anthropic/OTLP
endpoints — same container image (`Dockerfile`), different orchestrator.
Jaeger/Prometheus/Grafana are not yet represented in the Terraform
scaffolding — flagged as a real gap for whenever this infrastructure is
actually provisioned, not silently assumed away.
