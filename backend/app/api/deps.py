"""FastAPI dependencies shared across routers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Query
from redis.asyncio.client import Redis as RedisClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_redis, get_session
from app.core.errors import ValidationError

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[RedisClient, Depends(get_redis)]


async def get_project_id(
    project_id: Annotated[str | None, Query(description="Project UUID")] = None,
    x_project_id: Annotated[str | None, Header(alias="X-Project-Id")] = None,
) -> uuid.UUID:
    """Resolve the project scope from the query string or a header.

    v0.1 is intentionally unauthenticated: the client supplies the project id
    and the API trusts it. This is a deliberate simplification, not an oversight
    — see PLAN.md §13.
    """
    raw = project_id or x_project_id
    if not raw:
        raise ValidationError("project_id is required (query parameter or X-Project-Id header)")
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise ValidationError(f"project_id is not a valid UUID: {raw!r}") from exc


ProjectDep = Annotated[uuid.UUID, Depends(get_project_id)]


async def get_document_id(document_id: str) -> uuid.UUID:
    """Parse a `:document_id` path parameter."""
    try:
        return uuid.UUID(document_id)
    except ValueError as exc:
        raise ValidationError(f"document_id is not a valid UUID: {document_id!r}") from exc


async def dependency_session() -> AsyncIterator[AsyncSession]:
    """Alias kept for readability at call sites that need an explicit session."""
    async for session in get_session():
        yield session
