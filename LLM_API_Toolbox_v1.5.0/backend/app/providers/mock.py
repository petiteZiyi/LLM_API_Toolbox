import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.domain import (
    ChatRequest,
    ChatResult,
    FinishReason,
    ModelInfo,
    ProviderStatus,
    StreamEvent,
    Usage,
)
from app.errors import ProviderError


@dataclass(slots=True)
class MockBehavior:
    first_delay_seconds: float = 0.04
    chunk_delay_seconds: float = 0.012
    chunk_size: int = 2
    error_code: str | None = None
    error_after_chunks: int | None = None


class MockProvider:
    name = "mock"

    def __init__(self, behavior: MockBehavior | None = None) -> None:
        self.behavior = behavior or MockBehavior()

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            display_name="Mock",
            status="available",
        )

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="mock-echo-v1",
                display_name="Mock Echo v1",
                provider=self.name,
                default=True,
                max_output_tokens=8192,
            )
        ]

    def _answer(self, request: ChatRequest) -> str:
        last = request.messages[-1].content.strip()
        return (
            "这是 Mock Provider 的本地响应。\n\n"
            f"我已收到你的消息：“{last}”\n\n"
            "当前回复不消耗 API 额度，可用于检查多轮对话、流式显示和错误处理。"
        )

    def _raise_if_configured(self) -> None:
        code = self.behavior.error_code
        if not code:
            return
        mapping = {
            "auth": ProviderError(
                "PROVIDER_AUTH_FAILED", "Provider authentication failed.", 502, self.name, False
            ),
            "rate_limit": ProviderError(
                "RATE_LIMITED", "Provider rate limit reached.", 429, self.name, True
            ),
            "timeout": ProviderError(
                "PROVIDER_TIMEOUT", "Provider request timed out.", 504, self.name, True
            ),
            "upstream": ProviderError(
                "PROVIDER_UPSTREAM_ERROR", "Provider is unavailable.", 502, self.name, True
            ),
        }
        raise mapping.get(
            code,
            ProviderError("PROVIDER_UPSTREAM_ERROR", "Mock failure.", 502, self.name, False),
        )

    async def chat(self, request: ChatRequest) -> ChatResult:
        await asyncio.sleep(self.behavior.first_delay_seconds)
        self._raise_if_configured()
        answer = self._answer(request)
        input_tokens = sum(max(1, len(message.content) // 4) for message in request.messages)
        output_tokens = max(1, len(answer) // 4)
        return ChatResult(
            output_text=answer,
            provider=self.name,
            model="mock-echo-v1",
            finish_reason=FinishReason.STOP,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        await asyncio.sleep(self.behavior.first_delay_seconds)
        if self.behavior.error_after_chunks is None:
            self._raise_if_configured()
        answer = self._answer(request)
        chunks_sent = 0
        for offset in range(0, len(answer), self.behavior.chunk_size):
            if (
                self.behavior.error_after_chunks is not None
                and chunks_sent == self.behavior.error_after_chunks
            ):
                self._raise_if_configured()
            yield StreamEvent(type="delta", delta=answer[offset : offset + self.behavior.chunk_size])
            chunks_sent += 1
            await asyncio.sleep(self.behavior.chunk_delay_seconds)

        input_tokens = sum(max(1, len(message.content) // 4) for message in request.messages)
        output_tokens = max(1, len(answer) // 4)
        yield StreamEvent(
            type="done",
            finish_reason=FinishReason.STOP,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )

