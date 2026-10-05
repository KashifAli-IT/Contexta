"""Document upload, listing, retrieval and deletion.

Uploads are acknowledged immediately (<200 ms): the file is streamed to object
storage, a `PENDING` row is committed, an ingestion job is enqueued, and the
request returns 202. All parsing and embedding happens in the Arq worker.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import PurePosixPath
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ProjectDep, SessionDep
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationError
from app.core.events import event_stream
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.schemas.document import (
    DocumentListOut,
    DocumentOut,
    RetryAccepted,
    UploadAccepted,
    to_out,
)
from app.services.storage import StorageClient

router = APIRouter(prefix="/documents", tags=["documents"])
log = get_logger("contexta.documents")

JOB_INGEST = "ingest_document"


def _storage(request: Request) -> StorageClient:
    return request.app.state.storage  # type: ignore[no-any-return]


def _validate_upload(file: UploadFile, request: Request) -> str:
    """Check the extension and declared content type; return the file name."""
    settings = request.app.state.settings
    name = file.filename or "document.pdf"
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in settings.allowed_upload_extensions:
        raise ValidationError(
            f"unsupported file type {suffix or '(none)'!r}; "
            f"allowed: {', '.join(settings.allowed_upload_extensions)}"
        )
    declared = (file.content_type or "").lower()
    if declared and declared not in {"application/pdf", "application/octet-stream"}:
        raise ValidationError(f"unsupported content type {declared!r}; expected a PDF")
    return name


async def _enqueue_ingestion(request: Request, document_id: uuid.UUID) -> str | None:
    """Hand the document to the worker. Returns the Arq job id, if any."""
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        return None
    job = await pool.enqueue_job(JOB_INGEST, str(document_id))
    return job.job_id if job else None


async def _out_with_url(request: Request, document: Document) -> DocumentOut:
    """Serialise a document, attaching a fresh presigned file URL."""
    url: str | None = None
    try:
        url = await _storage(request).presigned_get(document.file_key)
    except Exception:  # a missing URL must not fail the listing
        log.warning("presign_failed", document_id=str(document.id))
    return to_out(document, file_url=url)


async def _load(session: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise NotFoundError(f"document {document_id} does not exist")
    return document


@router.post(
    "",
    response_model=UploadAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a PDF for asynchronous ingestion",
    responses={413: {"description": "File exceeds the configured size limit"}},
)
async def upload_document(
    request: Request,
    session: SessionDep,
    project_id: Annotated[uuid.UUID, Form(description="Project UUID that owns the document")],
    file: Annotated[UploadFile, File(description="The PDF to ingest")],
    title: Annotated[
        str | None, Form(description="Display title; defaults to the file name")
    ] = None,
) -> UploadAccepted:
    """Store the upload and queue ingestion. Returns as soon as it is durable."""
    settings = request.app.state.settings
    name = _validate_upload(file, request)

    if file.size is not None and file.size > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise PayloadTooLargeError(
            f"file is {file.size} bytes; the limit is {settings.max_upload_bytes} ({limit_mb} MB)"
        )

    document_id = uuid.uuid4()
    key = _storage(request).document_key(document_id, name)
    # Stream straight from the spooled upload: never buffer a large PDF in RAM.
    size = await _storage(request).upload_fileobj(file.file, key, content_type="application/pdf")
    await file.close()

    document = Document(
        id=document_id,
        title=(title or PurePosixPath(name).stem).strip()[:512] or "Untitled",
        file_key=key,
        content_type="application/pdf",
        size_bytes=size,
        status=DocumentStatus.PENDING,
        project_id=project_id,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    document.job_id = await _enqueue_ingestion(request, document.id)
    await session.commit()

    log.info(
        "upload_accepted",
        document_id=str(document.id),
        size_bytes=size,
        dispatched=document.job_id is not None,
    )
    return UploadAccepted(
        job_id=document.job_id or "",
        document_id=document.id,
        status=document.status,
    )


@router.get(
    "",
    response_model=DocumentListOut,
    status_code=status.HTTP_200_OK,
    summary="List a project's documents",
)
async def list_documents(
    request: Request,
    session: SessionDep,
    project_id: ProjectDep,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> DocumentListOut:
    """Newest first, with a presigned file URL per row."""
    total = await session.scalar(
        select(func.count()).select_from(Document).where(Document.project_id == project_id)
    )
    rows = (
        (
            await session.execute(
                select(Document)
                .where(Document.project_id == project_id)
                .order_by(Document.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return DocumentListOut(
        items=[await _out_with_url(request, row) for row in rows],
        total=int(total or 0),
    )


@router.get(
    "/events",
    status_code=status.HTTP_200_OK,
    summary="Server-sent document status stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "`document.status` frames as ingestion progresses",
        }
    },
)
async def document_events(request: Request, project_id: ProjectDep) -> StreamingResponse:
    """Stream ingestion progress for a project.

    A GET route, so the browser may use `EventSource`; `fetch` streaming also
    works. Emits a `resync` frame on connect, then one `document.status` frame
    per phase change, with a `: ping` heartbeat.
    """
    settings = request.app.state.settings
    redis = request.app.state.redis

    async def generator() -> AsyncIterator[str]:
        async for frame in event_stream(
            redis, project_id, heartbeat=settings.chat_heartbeat_seconds
        ):
            if await request.is_disconnected():
                break
            yield frame

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    status_code=status.HTTP_200_OK,
    summary="Fetch one document",
)
async def get_document(
    request: Request, session: SessionDep, document_id: uuid.UUID
) -> DocumentOut:
    document = await _load(session, document_id)
    return await _out_with_url(request, document)


@router.get(
    "/{document_id}/file",
    status_code=status.HTTP_302_FOUND,
    summary="Redirect to a presigned file URL",
    responses={302: {"description": "Redirect to a time-limited signed URL"}},
)
async def get_document_file(
    request: Request, session: SessionDep, document_id: uuid.UUID
) -> RedirectResponse:
    """302 redirect so the PDF never passes through the API.

    The bucket stays private: the browser receives only a signed, expiring URL.
    """
    document = await _load(session, document_id)
    if document.file_url:
        return RedirectResponse(url=document.file_url, status_code=status.HTTP_302_FOUND)
    url = await _storage(request).presigned_get(document.file_key)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/{document_id}/retry",
    response_model=RetryAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-queue a failed or stalled document",
)
async def retry_document(
    request: Request, session: SessionDep, document_id: uuid.UUID
) -> RetryAccepted:
    """Re-enqueue ingestion. Clears any previous error before dispatch."""
    document = await _load(session, document_id)
    document.status = DocumentStatus.PENDING
    document.error_message = None
    document.page_count = 0
    document.chunk_count = 0
    await session.commit()

    document.job_id = await _enqueue_ingestion(request, document.id)
    await session.commit()

    log.info("retry_queued", document_id=str(document.id), dispatched=bool(document.job_id))
    return RetryAccepted(
        job_id=document.job_id or "",
        document_id=document.id,
        status=document.status,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document, its chunks and its stored file",
)
async def delete_document(
    request: Request, session: SessionDep, document_id: uuid.UUID
) -> Response:
    document = await _load(session, document_id)
    key = document.file_key
    project_id = document.project_id

    await session.delete(document)
    await session.commit()

    # Object removal is best-effort: the database is the source of truth and a
    # stray object must not make DELETE fail.
    try:
        await _storage(request).delete(key)
    except Exception:  # best-effort teardown of external state
        log.warning("storage_delete_failed", document_id=str(document_id))

    hybrid = getattr(request.app.state, "hybrid", None)
    if hybrid is not None:
        try:
            await hybrid.delete_document(document_id)
        except Exception:  # best-effort teardown of external state
            log.warning("vector_delete_failed", document_id=str(document_id))

    log.info("deleted", document_id=str(document_id), project_id=str(project_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{document_id}/chunks",
    status_code=status.HTTP_200_OK,
    summary="List a document's chunks (debugging aid)",
)
async def list_chunks(
    session: SessionDep,
    document_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    """Expose the parsed chunks so ingestion output can be verified from the API."""
    from sqlalchemy import select as sa_select

    from app.models.chunk import DocumentChunk

    await _load(session, document_id)
    rows = (
        (
            await session.execute(
                sa_select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {
        "total": len(rows),
        "items": [
            {
                "id": str(row.id),
                "chunk_index": row.chunk_index,
                "page_number": row.page_number,
                "is_table": row.is_table,
                "has_summary": bool(row.summary),
                "embedding_id": row.embedding_id,
                "content": row.content[:400],
            }
            for row in rows
        ],
    }
