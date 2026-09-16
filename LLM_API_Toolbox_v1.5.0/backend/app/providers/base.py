from collections.abc import AsyncIterator
from typing import Protocol

from app.domain import ChatRequest, ChatResult, ModelInfo, ProviderStatus, StreamEvent


class BaseProvider(Protocol):
    name: str

    async def get_status(self) -> ProviderStatus: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def chat(self, request: ChatRequest) -> ChatResult: ...
    def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamEvent]: ...

