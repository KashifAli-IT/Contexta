"""Liveness and readiness probes."""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Request, Response, status

from app import __version__
from app.schemas.common import DependencyHealth, HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def health(request: Request) -> HealthResponse:
    """Always 200 while the process is serving requests."""
    settings = request.app.state.settings
    return HealthResponse(status="ok", version=__version__, environment=settings.app_env)


async def _timed(name: str, coro) -> DependencyHealth:  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    try:
        detail = await coro
        ok, message = True, detail or "ok"
    except Exception as exc:  # a probe must never raise
        ok, message = False, f"{type(exc).__name__}: {exc}"[:200]
    return DependencyHealth(
        name=name,
        status="ok" if ok else "error",
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
        detail=message,
    )


async def _check_postgres(request: Request) -> str:
    from sqlalchemy import text

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return "reachable"


async def _check_redis(request: Request) -> str:
    pong = await request.app.state.redis.ping()
    return "PONG" if pong else "no pong"


async def _check_qdrant(request: Request) -> str:
    """Qdrant is only wired into the app from Stage 6 onwards."""
    if not hasattr(request.app.state, "hybrid"):
        return "not configured yet"
    import httpx

    settings = request.app.state.settings
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{settings.qdrant_url}/collections")
        response.raise_for_status()
    return f"{len(response.json().get('result', {}).get('collections', []))} collection(s)"


async def _check_storage(request: Request) -> str:
    storage = request.app.state.storage
    exists = await storage.bucket_exists()
    return f"bucket '{storage.bucket}' {'present' if exists else 'MISSING'}"


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    responses={503: {"description": "One or more dependencies are unavailable"}},
)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Check every backing service concurrently; 503 if any is unavailable."""
    checks = await asyncio.gather(
        _timed("postgres", _check_postgres(request)),
        _timed("redis", _check_redis(request)),
        _timed("qdrant", _check_qdrant(request)),
        _timed("storage", _check_storage(request)),
    )
    healthy = all(check.status == "ok" for check in checks)
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if healthy else "degraded",
        checks=list(checks),
    )
