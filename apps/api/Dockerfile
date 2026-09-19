# Uma imagem para `api` (uvicorn) e `data` (worker): o compose troca só o `command`.
#   docker build -t alpherion-api apps/api
#   docker run alpherion-api                                  # API
#   docker run alpherion-api python -m alpherion.data.jobs.X  # um job do worker

FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM base AS runner
RUN groupadd --system --gid 1001 app && useradd --system --uid 1001 --gid app --home /app app
COPY --from=deps /app/.venv /app/.venv
COPY --chown=app:app alpherion ./alpherion
COPY --chown=app:app alembic.ini pyproject.toml ./
ENV PATH=/app/.venv/bin:$PATH
USER app
EXPOSE 8000
CMD ["uvicorn", "alpherion.main:app", "--host", "0.0.0.0", "--port", "8000"]
