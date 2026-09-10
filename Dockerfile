# Sprint 12 hardening: multi-stage build (builder installs/builds, runtime
# only ships what's needed) + non-root runtime user. Single-stage was
# intentionally used through Block 2/3 (see ADR-012) — this is where the
# spec slates the upgrade.

FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
COPY data ./data
RUN uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --from=builder --chown=app:app /app/src ./src
COPY --from=builder --chown=app:app /app/alembic.ini ./
COPY --from=builder --chown=app:app /app/migrations ./migrations
COPY --from=builder --chown=app:app /app/data ./data

# sentence-transformers/huggingface_hub download models into $HOME/.cache at
# request time (lazy-loaded); the app user's HOME is /app, but /app itself
# stays root-owned even after the --chown copies above, so create and own
# the cache dir explicitly or every first embedding/reranker call 500s with
# PermissionError.
RUN mkdir -p /app/.cache && chown -R app:app /app/.cache

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "cka.main:app", "--host", "0.0.0.0", "--port", "8000"]
