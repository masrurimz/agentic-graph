FROM ghcr.io/astral-sh/uv:python3.12-bookworm AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
COPY agentic_graph/ ./agentic_graph/

RUN uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV COGNEE_DATA_ROOT=/data \
    COGNEE_SYSTEM_ROOT=/system \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/agentic_graph /app/agentic_graph
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/uv.lock /app/uv.lock

VOLUME ["/data", "/system"]
EXPOSE 28195

CMD ["ag-server"]
