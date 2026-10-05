"""Redis pub/sub event bus for ingestion status.

The worker and the API are separate processes, so document status changes are
fanned out over Redis rather than shared in-process state. Publishing is
best-effort: a document reaching READY must never fail because nobody is
listening.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from redis.asyncio.client import PubSub
from redis.asyncio.client import Redis as RedisClient

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger("contexta.events")

GLOBAL_CHANNEL = "documents:all"


def document_channel(project_id: Any) -> str:
    """Channel carrying status changes for one project."""
    return f"documents:{project_id}"


def channels_for(project_id: Any) -> list[str]:
    """Channels a subscriber must listen on to see a project's events."""
    return [GLOBAL_CHANNEL, document_channel(project_id)]


async def publish_document_event(
    redis: RedisClient,
    project_id: Any,
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> None:
    """Publish a document status change to a project and to the global channel."""
    body = json.dumps(payload, default=str)
    try:
        await redis.publish(document_channel(project_id), body)
        await redis.publish(GLOBAL_CHANNEL, body)
    except Exception as exc:  # never fail ingestion on a notify error
        log.warning("publish_failed", project_id=str(project_id), error=str(exc))


@asynccontextmanager
async def subscription(redis: RedisClient, project_id: Any) -> AsyncIterator[list[PubSub]]:
    """Subscribe to both the project channel and the global channel."""
    subs: list[PubSub] = []
    try:
        for channel in channels_for(project_id):
            pubsub = redis.pubsub(ignore_subscribe_messages=True)
            await pubsub.subscribe(channel)
            subs.append(pubsub)
        yield subs
    finally:
        for pubsub in subs:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except Exception:  # best-effort teardown
                pass


async def event_stream(
    redis: RedisClient,
    project_id: Any,
    *,
    heartbeat: float = 15.0,
    stop: asyncio.Event | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames for document events until the consumer disconnects.

    Emits a `resync` frame immediately on connect so a freshly opened dashboard
    can hydrate without a second request, then a `: ping` comment every
    `heartbeat` seconds to keep intermediaries from closing the connection.
    """

    def frame(payload: dict[str, Any]) -> str:
        return f"data: {json.dumps(payload, default=str)}\n\n"

    yield frame({"event": "resync", "project_id": str(project_id)})

    async with subscription(redis, project_id) as subs:
        tasks = [
            asyncio.create_task(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0))
            for pubsub in subs
        ]
        try:
            while stop is None or not stop.is_set():
                done, _pending = await asyncio.wait(
                    tasks, timeout=heartbeat, return_when=asyncio.FIRST_COMPLETED
                )
                if not done:
                    yield ": ping\n\n"
                for task in done:
                    index = tasks.index(task)
                    try:
                        message = task.result()
                    except asyncio.CancelledError:
                        return
                    finally:
                        tasks[index] = asyncio.create_task(
                            subs[index].get_message(ignore_subscribe_messages=True, timeout=1.0)
                        )
                    if message and message.get("type") == "message":
                        try:
                            payload = json.loads(message["data"])
                        except (TypeError, ValueError):
                            continue
                        yield frame(payload)
        except asyncio.CancelledError:
            raise
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
