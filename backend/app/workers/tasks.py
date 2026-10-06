"""Arq background worker: document ingestion.

The worker owns every CPU/IO-heavy part of ingestion. It is a separate process
from the API so that a 500-page PDF can never occupy a request thread, and so
the parser and embedding model can be kept out of the API's memory profile.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

import structlog
from arq.connections import RedisSettings

from app.core.config import Settings, get_settings
from app.core.database import build_redis, dispose_database, session_factory
from app.services.ingestion import IngestionService
from app.services.llm import get_llm
from app.services.storage import StorageClient

log = structlog.get_logger("contexta.worker")

#: arq hands each job a plain dict shared by the process; it exports no type
#: for it (checked against arq 0.28), so the alias is declared here.
WorkerCtx = dict[str, Any]


def get_redis_settings() -> RedisSettings:
    """Connection settings derived from the application configuration."""
    cfg = get_settings()
    return RedisSettings.from_dsn(cfg.redis_url)


class IngestionContext:
    """Resources opened once per worker process."""

    def __init__(self) -> None:
        self.settings: Settings = get_settings()
        self.storage: StorageClient | None = None
        self.redis: Any = None
        self.service: IngestionService | None = None

    async def startup(self) -> None:
        self.storage = StorageClient(self.settings)
        await self.storage.ensure_bucket()
        self.redis = build_redis(self.settings)
        self.service = IngestionService(session_factory, self.storage, self.redis, self.settings)
        if self.settings.model_download_on_startup:
            # Warm the embedding model so the first real document is not slow.
            try:
                from app.services.embedding import EmbeddingService

                await EmbeddingService(self.settings).warmup()
            except ImportError:
                log.info("embedding_warmup_skipped", reason="not implemented yet")
            except Exception:  # warmup is best effort
                log.warning("embedding_warmup_failed")
        log.info("worker_startup", parser=self.settings.parser)

    async def shutdown(self) -> None:
        await get_llm().aclose()
        await dispose_database()
        if self.redis is not None:
            await self.redis.aclose()
        log.info("worker_shutdown")


async def startup(ctx: WorkerCtx) -> IngestionContext:
    """Arq `on_startup` hook."""
    context = IngestionContext()
    ctx["ingestion"] = context
    await context.startup()
    return context


async def shutdown(ctx: WorkerCtx) -> None:
    """Arq `on_shutdown` hook."""
    context = ctx.get("ingestion")
    if context is not None:
        await context.shutdown()


async def ingest_document(ctx: WorkerCtx, document_id: str) -> dict[str, Any]:
    """Run the ingestion pipeline for one document.

    Arq enqueues this by name from `POST /api/v1/documents`. The document row
    records the outcome, so a returned error status is not itself a job failure.
    """
    context: IngestionContext = ctx["ingestion"]
    assert context.service is not None, "worker startup did not complete"
    log.info("ingest_job_started", document_id=document_id)
    result = await context.service.ingest(uuid.UUID(document_id))
    log.info(
        "ingest_job_finished",
        document_id=document_id,
        status=result.status.value,
        chunks=result.chunk_count,
        duration_ms=round(result.duration_ms, 1),
    )
    return {
        "document_id": str(result.document_id),
        "status": result.status.value,
        "page_count": result.page_count,
        "chunk_count": result.chunk_count,
        "table_count": result.table_count,
        "duration_ms": round(result.duration_ms, 1),
        "error": result.error,
    }


class WorkerSettings:
    """Arq worker configuration."""

    functions: ClassVar[list] = [ingest_document]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()

    #: Ingestion is CPU-bound; oversubscribing the box makes every job slower.
    max_jobs = get_settings().arq_max_jobs
    job_timeout = get_settings().arq_job_timeout
    max_tries = 2
    keep_result = 3600
    health_check_interval = 30
    queue_name = "contexta:ingest"
