"""Arq background jobs.

Stub for Stage 3 (the worker image must build before ingestion exists).
Replaced by the real implementation in Stage 5.
"""

from __future__ import annotations

from typing import ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings


def get_redis_settings() -> RedisSettings:
    """Connection settings derived from the application configuration."""
    cfg = get_settings()
    return RedisSettings.from_dsn(cfg.redis_url)


class WorkerSettings:
    """Arq worker configuration (populated in Stage 5)."""

    functions: ClassVar[list] = []
    redis_settings: RedisSettings = get_redis_settings()
    max_jobs: int = 2
    job_timeout: int = 1800
