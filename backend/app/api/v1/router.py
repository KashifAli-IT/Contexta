"""v1 API router aggregation.

Feature routers are attached as they are built (see PLAN.md stages 4, 10, 11)
so that every commit is independently runnable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import documents, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router)

__all__ = ["api_router"]
