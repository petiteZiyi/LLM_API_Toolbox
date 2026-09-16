import asyncio
import random
from collections.abc import AsyncIterator

from app.config import Settings
from app.domain import ChatRequest, ChatResult, StreamEvent
from app.errors import AppError, ProviderError
from app.providers.base import BaseProvider
from app.registry import ProviderRegistry
from app.web_search import SearchUnavailableError, WebSearchService


class ChatService:
    def __init__(self, registry: ProviderRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        self.web_search = WebSearchService(
            timeout_seconds=settings.web_search_timeout_seconds,
            max_results=settings.web_search_max_results,
        )

    def _validate_limits(self, request: ChatRequest) -> None:
        if len(request.messages) > self.settings.max_messages:
            raise AppError("INVALID_REQUEST", "Too many messages.", 400)
        lengths = [len(message.content) for message in request.messages]
        if any(length > self.settings.max_message_chars for length in lengths):
            raise AppError("INVALID_REQUEST", "A message is too long.", 400)
        if sum(lengths) > self.settings.max_total_message_chars:
            raise AppError("INVALID_REQUEST", "The conversation is too long.", 400)
        if request.parameters.max_output_tokens > self.settings.max_output_tokens_limit:
            raise AppError("INVALID_REQUEST", "max_output_tokens exceeds the system limit.", 400)

    async def prepare(self, request: ChatRequest) -> BaseProvider:
        self._validate_limits(request)
        provider = await self.registry.validate_model(request.provider, request.model)
        status = await provider.get_status()
        if status.status != "available":
            from app.errors import not_configured

            raise not_configured(request.provider)
        if request.parameters.web_search_enabled:
            try:
                request.system_prompt = await self.web_search.enrich_system_prompt(
                    request.messages[-1].content,
                    request.system_prompt,
                )
            except SearchUnavailableError as exc:
                raise AppError(
                    "WEB_SEARCH_FAILED",
                    "Public web search is temporarily unavailable.",
                    502,
                    retryable=True,
                ) from exc
        return provider

    async def chat(self, request: ChatRequest) -> ChatResult:
        provider = await self.prepare(request)
        async with self._semaphore:
            async with asyncio.timeout(self.settings.request_total_timeout_seconds):
                for attempt in range(self.settings.max_retries + 1):
                    try:
                        return await provider.chat(request)
                    except ProviderError as exc:
                        if not exc.retryable or attempt >= self.settings.max_retries:
                            raise
                        await asyncio.sleep((2**attempt) + random.random() * 0.25)
        raise RuntimeError("unreachable")

    async def stream(
        self, request: ChatRequest, provider: BaseProvider | None = None
    ) -> AsyncIterator[StreamEvent]:
        provider = provider or await self.prepare(request)
        async with self._semaphore:
            async with asyncio.timeout(self.settings.request_total_timeout_seconds):
                for attempt in range(self.settings.max_retries + 1):
                    emitted_delta = False
                    try:
                        iterator = provider.stream_chat(request).__aiter__()
                        while True:
                            try:
                                event = await asyncio.wait_for(
                                    iterator.__anext__(),
                                    timeout=self.settings.stream_idle_timeout_seconds,
                                )
                            except StopAsyncIteration:
                                break
                            if event.type == "delta":
                                emitted_delta = True
                            yield event
                        return
                    except ProviderError as exc:
                        if emitted_delta or not exc.retryable or attempt >= self.settings.max_retries:
                            raise
                        await asyncio.sleep((2**attempt) + random.random() * 0.25)
