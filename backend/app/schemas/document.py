"""Request/response schemas for the documents API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import Document, DocumentStatus


class DocumentOut(BaseModel):
    """A document as exposed to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: DocumentStatus
    page_count: int
    chunk_count: int
    size_bytes: int
    content_type: str
    project_id: uuid.UUID
    error_message: str | None = None
    job_id: str | None = None
    #: Presigned, time-limited URL to the stored file.
    file_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int


class UploadAccepted(BaseModel):
    """202 response for an accepted upload."""

    job_id: str
    document_id: uuid.UUID
    status: DocumentStatus
    detail: str = "queued for ingestion"


class RetryAccepted(BaseModel):
    job_id: str
    document_id: uuid.UUID
    status: DocumentStatus
    detail: str = "re-queued for ingestion"


class DocumentEvent(BaseModel):
    """Payload broadcast on the document event stream."""

    event: str = Field(examples=["document.status"])
    document_id: uuid.UUID | str | None = None
    project_id: uuid.UUID | str | None = None
    status: str | None = None
    phase: str | None = None
    percent: float | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    error_message: str | None = None

    @classmethod
    def status_event(
        cls,
        document: Document,
        *,
        phase: str | None = None,
        percent: float | None = None,
    ) -> DocumentEvent:
        return cls(
            event="document.status",
            document_id=document.id,
            project_id=document.project_id,
            status=document.status.value,
            phase=phase,
            percent=percent,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            error_message=document.error_message,
        )


def to_out(document: Document, file_url: str | None = None) -> DocumentOut:
    """Convert a `Document` row into its API representation."""
    return DocumentOut(
        id=document.id,
        title=document.title,
        status=document.status,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        size_bytes=document.size_bytes,
        content_type=document.content_type,
        project_id=document.project_id,
        error_message=document.error_message,
        job_id=document.job_id,
        file_url=file_url or document.file_url,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
