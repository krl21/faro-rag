# Backend image with one target per role:
#   api    -> FastAPI (local embeddings)
#   worker -> Celery (local embeddings + Docling)
#   test   -> pytest and ruff (fake providers only, no PyTorch)
# Dependencies are installed before copying the code so they stay cached.

FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/data/hf-cache
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data/uploads /data/hf-cache \
    && chown -R app:app /data
WORKDIR /app
COPY pyproject.toml uv.lock ./

FROM base AS api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra local-embeddings
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra local-embeddings --extra docling
COPY --chown=app:app . .
USER app
CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=INFO", "--concurrency=2"]

FROM base AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
COPY --chown=app:app . .
USER app
CMD ["pytest", "-v"]
