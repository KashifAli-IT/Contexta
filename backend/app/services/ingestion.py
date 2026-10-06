"""Ingestion orchestrator.

Drives a document from stored object to searchable chunks, publishing a status
event and updating the database row at every phase boundary:

    FETCHING -> PARSING -> CHUNKING -> SUMMARIZING -> EMBEDDING -> INDEXING -> READY
                                                                       \\-> FAILED

The EMBEDDING/INDEXING phases are supplied by `services.index` (Stage 6). Until
that module exists the pipeline stops after SUMMARIZING, which keeps each
stage independently runnable.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.events import publish_document_event
from app.models.chunk import DocumentChunk
from app.models.document import Document, DocumentStatus
from app.services.chunker import ChunkDraft, build_drafts
from app.services.llm import LLMUnavailableError, get_llm
from app.services.parser import parse_pdf
from app.services.storage import StorageClient

log = structlog.get_logger("contexta.ingestion")

SUMMARY_MAX_TOKENS = 120
SUMMARY_CONCURRENCY = 5


class Phase(StrEnum):
    FETCHING = "FETCHING"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    SUMMARIZING = "SUMMARIZING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"


#: Fraction of the way through the pipeline, for the UI progress bar.
_PROGRESS: dict[Phase, float] = {
    Phase.FETCHING: 0.05,
    Phase.PARSING: 0.20,
    Phase.CHUNKING: 0.55,
    Phase.SUMMARIZING: 0.70,
    Phase.EMBEDDING: 0.85,
    Phase.INDEXING: 0.95,
    Phase.READY: 1.0,
    Phase.FAILED: 1.0,
}

SUMMARY_PROMPT = (
    "Summarise the following table in at most 25 words. State what the table "
    "compares or lists, and include any category names. Reply with the summary "
    "only, no preamble.\n\nTable:\n"
)


@dataclass
class IngestionResult:
    document_id: uuid.UUID
    status: DocumentStatus
    page_count: int
    chunk_count: int
    table_count: int
    duration_ms: float
    error: str | None = None


class IngestionService:
    """Runs the pipeline for one document at a time."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: StorageClient,
        redis: Any,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.storage = storage
        self.redis = redis
        self.settings = settings or get_settings()

    # ------------------------------------------------------------- utilities
    async def _load_document(self, document_id: uuid.UUID) -> Document:
        async with self.session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                raise LookupError(f"document {document_id} not found")
            return document

    async def _set_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        phase: Phase,
        *,
        error: str | None = None,
        page_count: int | None = None,
        chunk_count: int | None = None,
    ) -> None:
        """Persist a status transition and broadcast it."""
        async with self.session_factory() as session:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = status
            if error is not None:
                document.error_message = error[:4000]
            if page_count is not None:
                document.page_count = page_count
            if chunk_count is not None:
                document.chunk_count = chunk_count
            await session.commit()
            payload = {
                "event": "document.status",
                "document_id": str(document.id),
                "project_id": str(document.project_id),
                "status": status.value,
                "phase": phase.value,
                "percent": _PROGRESS[phase],
                "page_count": document.page_count,
                "chunk_count": document.chunk_count,
                "error_message": document.error_message,
            }
        await publish_document_event(
            self.redis, payload["project_id"], payload, settings=self.settings
        )

    # ---------------------------------------------------------------- phases
    async def _summarise_tables(self, drafts: list[ChunkDraft]) -> None:
        """Attach a short LLM summary to each table chunk, in place.

        Failures are non-fatal: a table without a summary is still retrievable
        by its cell values.
        """
        tables = [draft for draft in drafts if draft.is_table]
        if not tables:
            return
        llm = get_llm()
        if not llm.available:
            log.info("summaries_skipped", count=len(tables), reason="no llm backend")
            return
        semaphore = asyncio.Semaphore(SUMMARY_CONCURRENCY)

        async def summarise(draft: ChunkDraft) -> None:
            async with semaphore:
                try:
                    text = await llm.chat(
                        [{"role": "user", "content": SUMMARY_PROMPT + draft.content}],
                        max_tokens=SUMMARY_MAX_TOKENS,
                    )
                except (LLMUnavailableError, Exception):
                    log.warning("table_summary_failed")
                    return
                summary = (text or "").strip()
                if summary:
                    draft.summary = summary

        await asyncio.gather(*(summarise(draft) for draft in tables))

    async def _persist_chunks(
        self, session: AsyncSession, document_id: uuid.UUID, drafts: list[ChunkDraft]
    ) -> list[DocumentChunk]:
        """Replace any previous chunks, then insert the new set."""
        await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        rows: list[DocumentChunk] = []
        for index, draft in enumerate(drafts):
            rows.append(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    parent_chunk_id=None,
                    content=draft.content,
                    summary=draft.summary,
                    page_number=draft.page_number,
                    is_table=draft.is_table,
                    embedding_id=f"{document_id}:{index}",
                    chunk_index=index,
                    char_start=draft.char_start,
                    char_end=draft.char_end,
                )
            )
        session.add_all(rows)
        await session.flush()
        return rows

    # ------------------------------------------------------------------- run
    async def ingest(self, document_id: uuid.UUID) -> IngestionResult:
        """Execute the full pipeline for one document."""
        loop = asyncio.get_running_loop()
        started = loop.time()
        document = await self._load_document(document_id)
        table_count = 0

        try:
            await self._set_status(document_id, DocumentStatus.PROCESSING, Phase.FETCHING)

            data = await self.storage.download_bytes(document.file_key)

            await self._set_status(document_id, DocumentStatus.PROCESSING, Phase.PARSING)
            parsed = await parse_pdf(data, settings=self.settings)
            table_count = sum(len(page.tables) for page in parsed.pages)
            log.info(
                "parsed",
                document_id=str(document_id),
                pages=parsed.page_count,
                tables=table_count,
            )

            await self._set_status(
                document_id,
                DocumentStatus.PROCESSING,
                Phase.CHUNKING,
                page_count=parsed.page_count,
            )
            drafts = build_drafts(parsed, self.settings)

            await self._set_status(document_id, DocumentStatus.PROCESSING, Phase.SUMMARIZING)
            await self._summarise_tables(drafts)

            # Stages 6+ insert EMBEDDING/INDEXING here, before the rows are
            # committed as READY, so a document is never searchable-but-broken.
            indexed = await self._index(drafts, document)

            async with self.session_factory() as session:
                await self._persist_chunks(session, document_id, drafts)
                await session.commit()

            await self._set_status(
                document_id,
                DocumentStatus.READY,
                Phase.READY,
                page_count=parsed.page_count,
                chunk_count=len(drafts),
            )
            duration_ms = (loop.time() - started) * 1000
            log.info(
                "ingested",
                document_id=str(document_id),
                chunks=len(drafts),
                pages=parsed.page_count,
                tables=table_count,
                indexed=indexed,
                duration_ms=round(duration_ms, 1),
            )
            return IngestionResult(
                document_id=document_id,
                status=DocumentStatus.READY,
                page_count=parsed.page_count,
                chunk_count=len(drafts),
                table_count=table_count,
                duration_ms=duration_ms,
            )

        except Exception as exc:  # surfaced to the document row
            message = f"{type(exc).__name__}: {exc}"
            log.exception("ingestion_failed", document_id=str(document_id))
            await self._set_status(document_id, DocumentStatus.FAILED, Phase.FAILED, error=message)
            return IngestionResult(
                document_id=document_id,
                status=DocumentStatus.FAILED,
                page_count=0,
                chunk_count=0,
                table_count=table_count,
                duration_ms=(loop.time() - started) * 1000,
                error=message,
            )

    async def _index(self, drafts: list[ChunkDraft], document: Document) -> bool:
        """Embed and index chunks when the vector layer is available.

        Returns ``True`` when indexing ran. This indirection keeps Stage 5
        runnable before `services.index` exists and is the single place the
        dense+sparse pipeline hooks in.
        """
        try:
            from app.services.index import index_document
        except ImportError:
            log.info("indexing_skipped", reason="services.index not available")
            return False
        await self._set_status(document.id, DocumentStatus.PROCESSING, Phase.EMBEDDING)
        await index_document(
            document,
            drafts,
            settings=self.settings,
            on_phase=lambda: self._set_status(
                document.id, DocumentStatus.PROCESSING, Phase.INDEXING
            ),
        )
        return True


async def count_chunks(session: AsyncSession, document_id: uuid.UUID) -> int:
    """Utility used by tests and the debug endpoint."""
    result = await session.execute(
        select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)
    )
    return len(result.all())
