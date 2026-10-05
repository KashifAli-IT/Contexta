"""Shared Pydantic response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: Any | None = None


class ErrorEnvelope(BaseModel):
    """`{"error": {...}}` — the shape of every non-2xx response."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    version: str
    environment: str


class DependencyHealth(BaseModel):
    name: str
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    checks: list[DependencyHealth]
