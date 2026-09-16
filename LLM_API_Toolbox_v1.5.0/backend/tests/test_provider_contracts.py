from types import SimpleNamespace

import pytest

from app.domain import ChatRequest
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.openai_provider import OpenAIProvider
from app.secrets import EnvSecretStore


def request(provider: str, model: str) -> ChatRequest:
    return ChatRequest.model_validate(
        {
            "provider": provider,
            "model": model,
            "messages": [
                {"role": "user", "content": "问题"},
                {"role": "assistant", "content": "旧回答"},
                {"role": "user", "content": "继续"},
            ],
            "system_prompt": "系统指令",
            "parameters": {"temperature": 0.4, "max_output_tokens": 321},
        }
    )


class FakeResponses:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if kwargs.get("stream"):
            async def events():
                yield SimpleNamespace(type="response.output_text.delta", delta="Open")
                yield SimpleNamespace(type="response.output_text.delta", delta="AI")
                yield SimpleNamespace(
                    type="response.completed",
                    response=SimpleNamespace(
                        usage=SimpleNamespace(input_tokens=3, output_tokens=2, total_tokens=5)
                    ),
                )
            return events()
        return SimpleNamespace(
            output_text="OpenAI answer",
            model="openai-test",
            status="completed",
            incomplete_details=None,
            usage=SimpleNamespace(input_tokens=3, output_tokens=2, total_tokens=5),
        )


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponses()


@pytest.mark.asyncio
async def test_openai_request_response_and_stream_contract():
    client = FakeOpenAIClient()
    provider = OpenAIProvider(
        EnvSecretStore({"openai": "test-secret"}),
        ["openai-test"],
        client_factory=lambda _: client,
    )
    req = request("openai", "openai-test")
    result = await provider.chat(req)
    assert client.responses.kwargs["instructions"] == "系统指令"
    assert client.responses.kwargs["max_output_tokens"] == 321
    assert client.responses.kwargs["input"][0] == {"role": "user", "content": "问题"}
    assert result.output_text == "OpenAI answer"
    assert result.finish_reason == "stop"
    events = [event async for event in provider.stream_chat(req)]
    assert "".join(event.delta or "" for event in events if event.type == "delta") == "OpenAI"
    assert events[-1].type == "done"
    assert events[-1].usage.total_tokens == 5


class FakeAnthropicStream:
    text_stream = None

    def __init__(self):
        async def texts():
            yield "Anthropic"
            yield " answer"
        self.text_stream = texts()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get_final_message(self):
        return SimpleNamespace(
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=4, output_tokens=2),
        )


class FakeMessages:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Anthropic answer")],
            model="anthropic-test",
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=4, output_tokens=2),
        )

    def stream(self, **kwargs):
        self.kwargs = kwargs
        return FakeAnthropicStream()


class FakeAnthropicClient:
    def __init__(self):
        self.messages = FakeMessages()


@pytest.mark.asyncio
async def test_anthropic_request_response_and_stream_contract():
    client = FakeAnthropicClient()
    provider = AnthropicProvider(
        EnvSecretStore({"anthropic": "test-secret"}),
        ["anthropic-test"],
        client_factory=lambda _: client,
    )
    req = request("anthropic", "anthropic-test")
    result = await provider.chat(req)
    assert client.messages.kwargs["system"] == "系统指令"
    assert client.messages.kwargs["messages"][-1]["role"] == "user"
    assert client.messages.kwargs["max_tokens"] == 321
    assert result.output_text == "Anthropic answer"
    events = [event async for event in provider.stream_chat(req)]
    assert "".join(event.delta or "" for event in events if event.type == "delta") == "Anthropic answer"
    assert events[-1].finish_reason == "stop"
    assert events[-1].usage.total_tokens == 6


class FakeCompletions:
    def __init__(self):
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="compatible answer"),
                finish_reason="stop",
            )],
            model="compatible-test",
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3, total_tokens=8),
        )


@pytest.mark.asyncio
async def test_openai_compatible_contract_uses_system_message():
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenAICompatibleProvider(
        "deepseek",
        "DeepSeek",
        "https://example.test/v1",
        EnvSecretStore({"deepseek": "test-secret"}),
        ["compatible-test"],
        client_factory=lambda *_: client,
    )
    result = await provider.chat(request("deepseek", "compatible-test"))
    assert completions.kwargs["messages"][0] == {"role": "system", "content": "系统指令"}
    assert completions.kwargs["max_tokens"] == 321
    assert result.usage.total_tokens == 8

