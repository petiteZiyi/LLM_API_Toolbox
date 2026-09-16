import asyncio

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.domain import ChatRequest
from app.errors import ProviderError
from app.providers.mock import MockBehavior, MockProvider
from app.registry import ProviderRegistry
from app.service import ChatService


def payload(**overrides) -> ChatRequest:
    body = {
        "provider": "mock",
        "model": "mock-echo-v1",
        "messages": [{"role": "user", "content": "test"}],
        "parameters": {"temperature": 0.5, "max_output_tokens": 100},
    }
    body.update(overrides)
    return ChatRequest.model_validate(body)


def test_last_message_must_be_user():
    with pytest.raises(ValidationError):
        payload(messages=[{"role": "assistant", "content": "bad"}])


@pytest.mark.asyncio
async def test_service_rejects_system_token_limit():
    settings = Settings(_env_file=None, max_output_tokens_limit=10)
    service = ChatService(ProviderRegistry([MockProvider()]), settings)
    with pytest.raises(Exception) as caught:
        await service.chat(payload(parameters={"temperature": 0.5, "max_output_tokens": 11}))
    assert getattr(caught.value, "code", None) == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_retryable_error_is_retried(monkeypatch):
    provider = MockProvider(MockBehavior(error_code="rate_limit"))
    calls = 0

    async def chat(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ProviderError("RATE_LIMITED", "wait", 429, "mock", True)
        return await MockProvider().chat(request)

    provider.chat = chat  # type: ignore[method-assign]

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    settings = Settings(_env_file=None, max_retries=1)
    result = await ChatService(ProviderRegistry([provider]), settings).chat(payload())
    assert result.provider == "mock"
    assert calls == 2


@pytest.mark.asyncio
async def test_stream_does_not_retry_after_delta(monkeypatch):
    provider = MockProvider(
        MockBehavior(error_code="upstream", error_after_chunks=1, chunk_delay_seconds=0)
    )

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    settings = Settings(_env_file=None, max_retries=2)
    service = ChatService(ProviderRegistry([provider]), settings)
    events = []
    with pytest.raises(ProviderError):
        async for event in service.stream(payload()):
            events.append(event)
    assert len(events) == 1
    assert events[0].type == "delta"

