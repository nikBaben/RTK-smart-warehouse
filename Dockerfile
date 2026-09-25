FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/backend/.venv/bin:$PATH"

WORKDIR /backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libpq5 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /uvx /bin/


FROM base AS dependencies

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --frozen \
        --no-dev \
        --no-install-project


FROM base AS development

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --frozen \
        --no-install-project

COPY . .

EXPOSE 8000

CMD [
    "uvicorn",
    "backend.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
    "--reload"
]


FROM python:3.12-slim-bookworm AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/backend/.venv/bin:$PATH"

WORKDIR /backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libpq5 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=dependencies /backend/.venv /backend/.venv


COPY backend ./backend

COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

COPY models_store ./models_store

COPY tools/websocat /usr/local/bin/websocat

RUN chmod +x /usr/local/bin/websocat


RUN groupadd --system backend \
    && useradd \
        --system \
        --gid backend \
        --home-dir /backend \
        backend \
    && chown -R backend:backend /backend

USER backend


EXPOSE 8000

CMD [
    "uvicorn",
    "backend.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]