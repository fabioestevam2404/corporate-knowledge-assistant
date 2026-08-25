FROM python:3.12-slim

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

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "cka.main:app", "--host", "0.0.0.0", "--port", "8000"]
