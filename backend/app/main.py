"""ASGI application factory."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import Message, Receive, Scope, Send

from app import __version__
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import build_redis, dispose_database, session_factory
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging

log = structlog.get_logger("contexta.app")

REQUEST_ID_HEADER = "X-Request-ID"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start shared clients, then release them on shutdown."""
    settings: Settings = app.state.settings
    configure_logging(settings)
    log.info(
        "startup",
        version=__version__,
        env=settings.app_env,
        parser=settings.parser,
        llm_backend=settings.llm_backend,
    )

    app.state.session_factory = session_factory
    app.state.redis = build_redis(settings)

    # Object storage. Imported lazily so that importing the app stays cheap.
    from app.services.storage import StorageClient

    storage = StorageClient(settings)
    await storage.ensure_bucket()
    app.state.storage = storage

    log.info("startup_complete", bucket=settings.minio_bucket)
    try:
        yield
    finally:
        log.info("shutdown")
        await dispose_database()
        redis_client = getattr(app.state, "redis", None)
        if redis_client is not None:
            await redis_client.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application."""
    resolved = settings or get_settings()
    app = FastAPI(
        title="Contexta Py",
        version=__version__,
        description=(
            "Async multi-agent RAG platform: background PDF ingestion, "
            "hybrid retrieval, agentic answering over SSE, and neural TTS."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.settings = resolved

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, "X-Accel-Buffering"],
    )
    app.add_middleware(RequestContextMiddleware)

    install_error_handlers(app)
    app.include_router(api_router, prefix=resolved.api_v1_prefix)
    return app


class RequestContextMiddleware:
    """Assign a request id, log timing, and expose it on the response.

    Implemented as raw ASGI middleware rather than `BaseHTTPMiddleware` on
    purpose: the chat and document-event endpoints are long-lived SSE streams,
    and the base class adds a task/queue hop that delays the first frame.
    """

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers_list = MutableHeaders(scope=message)
                headers_list[REQUEST_ID_HEADER] = request_id
                # Disable proxy buffering so SSE frames reach the client at once.
                headers_list["X-Accel-Buffering"] = "no"
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            log.exception(
                "request_failed",
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=status_code,
                duration_ms=elapsed,
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            if elapsed > 1000:
                log.warning(
                    "slow_request",
                    method=scope.get("method"),
                    path=scope.get("path"),
                    status_code=status_code,
                    duration_ms=elapsed,
                )


app = create_app()

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
