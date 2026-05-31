FROM oven/bun:1 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ .
ARG PUBLIC_DEVDOCS_URL=http://localhost:9292
ENV PUBLIC_DEVDOCS_URL=$PUBLIC_DEVDOCS_URL
RUN bun run build

FROM python:3.14-slim
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --frozen

COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/build ./frontend/build

EXPOSE 5001
CMD ["uv", "run", "python", "-u", "backend/app.py"]
