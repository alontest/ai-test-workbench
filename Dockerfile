# 多阶段：Node 22 构建 web/dist → Python 3.14-slim 运行（ADR-027）。
# 密钥与 .env 不进入镜像。

FROM node:22-alpine AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.14-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:${PATH}" \
    AW_DATA_DIR=/data

WORKDIR /app

RUN useradd --system --uid 10001 --create-home --home-dir /app appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY scripts/docker-entrypoint.sh /app/scripts/docker-entrypoint.sh
COPY --from=frontend /web/dist /app/web/dist

RUN uv sync --frozen --no-dev \
    && rm -f /bin/uv /bin/uvx \
    && chmod 0755 /app/scripts/docker-entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
