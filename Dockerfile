FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libpq5 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM dependencies AS development
COPY tests ./tests
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY models_store ./models_store
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY --from=dependencies /opt/venv /opt/venv
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY models_store ./models_store
RUN groupadd --system backend \
    && useradd --system --gid backend --home-dir /backend backend \
    && chown -R backend:backend /backend
USER backend
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
