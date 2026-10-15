# Image for the upstream records API. Lives outside upstream/ because that folder is
# read-only for us (see CLAUDE.md); docker-compose.yml builds it with upstream/ as context.
#
# `uv run upstream` binds 127.0.0.1, which is unreachable from other containers, so we
# start the same app factory through uvicorn on 0.0.0.0 instead. Env vars
# (UPSTREAM_SLOW_RATE, UPSTREAM_TIMEOUT_RATE) are read by create_app and still apply.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
EXPOSE 8081
CMD ["uv", "run", "--no-sync", "uvicorn", "records_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8081"]
