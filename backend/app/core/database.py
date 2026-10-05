"""Async SQLAlchemy engine, session factory, and shared connection singletons."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.client import Redis as RedisClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def build_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create the async engine.

    Creating an engine performs no I/O; connections are opened lazily on first
    use, so importing this module is safe before the database is reachable.
    """
    cfg = settings or get_settings()
    return create_async_engine(
        cfg.database_url,
        echo=cfg.db_echo,
        pool_pre_ping=True,
        pool_size=cfg.db_pool_size,
        max_overflow=cfg.db_max_overflow,
        pool_recycle=1800,
    )


engine: AsyncEngine = build_engine()

session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)

_redis_pool: ConnectionPool | None = None


def build_redis(settings: Settings | None = None) -> RedisClient:
    """Create a Redis client backed by a connection pool."""
    cfg = settings or get_settings()
    pool = ConnectionPool.from_url(
        cfg.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=32,
    )
    return Redis(connection_pool=pool)


async def get_redis(request: Request) -> RedisClient:
    """FastAPI dependency yielding the process-wide Redis client.

    The client is created during application startup and cached on
    `app.state.redis`, so every request shares one connection pool. Tests may
    override this dependency with their own stub.
    """
    client = getattr(request.app.state, "redis", None)
    if client is None:
        client = build_redis()
        request.app.state.redis = client
    return client  # type: ignore[no-any-return]


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_database() -> None:
    """Close pooled connections on shutdown."""
    await engine.dispose()
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()  # type: ignore[attr-defined]
        _redis_pool = None


def db_metadata() -> Any:
    """Return the metadata object (import models first so tables register)."""
    from app import models  # noqa: F401  # side-effecting import

    return Base.metadata
