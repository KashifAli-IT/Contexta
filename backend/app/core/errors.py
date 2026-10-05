"""Uniform error handling.

Every failure leaves the API as::

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

`request_id` matches the `X-Request-ID` response header, so a failing request
can be traced through the logs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("contexta.errors")

#: Maps a few common Starlette/FastAPI status codes onto stable machine codes.
_HTTP_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_error",
    503: "service_unavailable",
    504: "upstream_timeout",
}


class AppError(Exception):
    """Base class for expected, client-reportable failures."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class UpstreamError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"


def error_envelope(
    code: str,
    message: str,
    request_id: str,
    details: Any | None = None,
) -> dict[str, Any]:
    """Build the canonical error body."""
    error: dict[str, Any] = {"code": code, "message": message, "request_id": request_id}
    if details is not None:
        error["details"] = details
    return {"error": error}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Render an `AppError` as the canonical envelope."""
    logger.info("app_error code=%s detail=%s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message, _request_id(request), exc.details),
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Render `HTTPException` (including 404s) as the canonical envelope."""
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    detail = exc.detail if isinstance(exc.detail, str) else "request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(code, detail, _request_id(request)),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Render request-body/query validation failures with field detail."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_envelope(
            "validation_error",
            "request payload failed validation",
            _request_id(request),
            details=exc.errors(),
        ),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler: log the traceback, return an opaque 500."""
    logger.exception("unhandled_error path=%s", request.url.path, exc_info=exc)
    message = "internal server error"
    if not getattr(request.app.state, "settings", None) or request.app.state.settings.app_env in {
        "development",
        "test",
    }:
        message = f"{type(exc).__name__}: {exc}"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_envelope("internal_error", message, _request_id(request)),
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register every handler on the application."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
