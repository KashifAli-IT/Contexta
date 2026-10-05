# syntax=docker/dockerfile:1
# Multi-stage image. `base` holds the dependency set; `api` and `worker` are
# thin runtime layers over it so both share one cached pip layer.
#
# Dependency pins in requirements.txt are resolved for CPython 3.12 (see
# requirements.in); do not relax them casually.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    MPLCONFIGDIR=/tmp/matplotlib

# curl -> container healthcheck; libgl/libglib -> PyMuPDF rendering;
# tini -> correct signal handling for arq/uvicorn workers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libglib2.0-0 \
        libgl1 \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency layer first: copied on its own so source edits do not invalidate it.
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY main.py ./main.py
# Tool configuration must be inside the image: the documented one-off commands
# (ruff / mypy / pytest) run in the container and must use the project settings.
COPY pyproject.toml ./pyproject.toml

# ---------------------------------------------------------------- api runtime
FROM base AS api
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=45s --retries=12 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]

# ------------------------------------------------------------- worker runtime
FROM base AS worker
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["arq", "app.workers.tasks.WorkerSettings"]
