FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
COPY packages/agentic-graph/ ./packages/agentic-graph/

RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_ROOT_DIRECTORY=/data \
    SYSTEM_ROOT_DIRECTORY=/system \
    ENOLA_AUTO_INSTALL=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/packages /app/packages
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock /app/uv.lock

VOLUME ["/data", "/system"]
EXPOSE 28195

CMD ["ag-server"]
