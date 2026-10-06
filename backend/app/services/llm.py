"""LLM access layer.

A single async client is used by every component that needs the model
(table summarisation in the worker, the agent graph in the API). Setting
``LLM_BACKEND=mock`` swaps in a deterministic stub so tests and offline demos
never touch the network.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterable
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings, get_settings

log = structlog.get_logger("contexta.llm")

Message = dict[str, Any]


class LLMUnavailableError(RuntimeError):
    """Raised when no LLM backend is configured (e.g. missing API key)."""


def _is_retryable(exc: Exception) -> bool:
    """Retry transport/rate-limit errors, but not bad requests."""
    name = type(exc).__name__
    return name in {
        "APIConnectionError",
        "APITimeoutError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
    }


class LLMClient:
    """Async chat client with retries and a deterministic offline stub."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None
        if self.settings.llm_backend == "groq" and self.settings.groq_api_key:
            self._client = AsyncOpenAI(
                api_key=self.settings.groq_api_key,
                base_url=self.settings.groq_base_url,
                timeout=self.settings.llm_timeout,
                max_retries=2,
            )
        elif self.settings.llm_backend == "groq":
            log.warning("llm_key_missing", model=self.settings.llm_model)

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def model(self) -> str:
        return self.settings.llm_model

    def _require(self) -> AsyncOpenAI:
        if self._client is None:
            raise LLMUnavailableError(
                "no LLM backend configured; set GROQ_API_KEY or LLM_BACKEND=mock"
            )
        return self._client

    def _complete(self, **kwargs: Any) -> str:
        """Synchronous mock completion, mirroring the streaming interface."""
        messages: Iterable[Message] = kwargs.get("messages", [])
        last = ""
        for message in messages:
            if message.get("role") == "user":
                last = str(message.get("content", ""))
        if not last:
            return "mock: no prompt supplied"
        if last.strip().startswith("{"):
            # Router/grader style prompts expect JSON back.
            try:
                request = json.loads(last)
            except ValueError:
                request = {}
            if "intent" in request or "query" in request:
                return json.dumps({"intent": "document", "rewritten_query": last})
            if "relevant" in request or "score" in request:
                return json.dumps({"relevant": True, "score": 85, "reason": "mock grader"})
        return f"mock answer for: {last[:120]}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        """Return the assistant's full reply as a single string."""
        if self._client is None:
            if self.settings.llm_backend == "mock":
                return self._complete(messages=messages)
            self._require()
        assert self._client is not None
        response = await self._client.chat.completions.create(
            model=model or self.settings.llm_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.settings.llm_temperature if temperature is None else temperature,
            max_tokens=max_tokens or self.settings.llm_max_tokens,
        )
        return response.choices[0].message.content or ""

    async def astream(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield reply text incrementally.

        Falls back to word-by-word emission for the mock backend so the SSE
        contract is exercised identically in tests and in production.
        """
        if self._client is None:
            if self.settings.llm_backend != "mock":
                self._require()
            text = self._complete(messages=messages)
            for word in text.split(" "):
                yield word + " "
                await asyncio.sleep(0)
            return
        stream = await self._client.chat.completions.create(
            model=model or self.settings.llm_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.settings.llm_temperature if temperature is None else temperature,
            max_tokens=max_tokens or self.settings.llm_max_tokens,
            stream=True,
        )
        async for chunk in cast("AsyncStream[ChatCompletionChunk]", stream):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    """Return the process-wide client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def set_llm(client: LLMClient | None) -> None:
    """Override the singleton (used by tests)."""
    global _client
    _client = client
