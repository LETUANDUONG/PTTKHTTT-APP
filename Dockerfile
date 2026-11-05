FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home hoodoo
COPY requirements-ai.txt ./
ARG PYPI_INDEX=https://mirrors.aliyun.com/pypi/simple/
RUN --mount=from=ghcr.io/astral-sh/uv:0.13.7,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=120 uv pip install --system --index $PYPI_INDEX \
    --index-strategy unsafe-first-match -r requirements-ai.txt
COPY backend/ backend/
COPY data/ data/
COPY scripts/ scripts/
COPY tests/ tests/
COPY run.py pytest.ini ./
COPY frontend/public/ frontend/public/
COPY --from=frontend /build/dist/ frontend/dist/
RUN chown -R hoodoo:hoodoo /app
USER hoodoo
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
