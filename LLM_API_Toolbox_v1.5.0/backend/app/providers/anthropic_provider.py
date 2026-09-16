from collections.abc import AsyncIterator, Callable
from typing import Any

from anthropic import AsyncAnthropic

from app.domain import ChatRequest, ChatResult, ModelInfo, ProviderStatus, StreamEvent
from app.errors import ProviderError, not_configured
from app.providers.utils import normalize_finish_reason, normalize_usage, translate_provider_exception, value
from app.secrets import SecretStore


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        secret_store: SecretStore,
        models: list[str],
        client_factory: Callable[[str], Any] | None = None,
        base_url: str | None = None,
    ) -> None:
        self.secret_store = secret_store
        self.models = models
        self.base_url = base_url
        self.client_factory = client_factory or (
            lambda key: AsyncAnthropic(api_key=key, base_url=base_url, max_retries=0)
        )

    async def _client(self) -> Any:
        key = await self.secret_store.get_secret(self.name)
        if not key:
            raise not_configured(self.name)
        return self.client_factory(key)

    async def get_status(self) -> ProviderStatus:
        available = bool(await self.secret_store.get_secret(self.name))
        return ProviderStatus(
            name=self.name,
            display_name="Anthropic",
            status="available" if available else "unavailable",
            reason_code=None if available else "NOT_CONFIGURED",
        )

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=model,
                display_name=model,
                provider=self.name,
                default=index == 0,
            )
            for index, model in enumerate(self.models)
        ]

    def _kwargs(self, request: ChatRequest) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "max_tokens": request.parameters.max_output_tokens,
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt
        if request.parameters.temperature is not None:
            kwargs["temperature"] = request.parameters.temperature
        return kwargs

    @staticmethod
    def _text(content: Any) -> str:
        return "".join(
            value(block, "text", "") or ""
            for block in content or []
            if value(block, "type") == "text"
        )

    async def chat(self, request: ChatRequest) -> ChatResult:
        client = await self._client()
        try:
            response = await client.messages.create(**self._kwargs(request))
            return ChatResult(
                output_text=self._text(value(response, "content", [])),
                provider=self.name,
                model=value(response, "model", request.model),
                finish_reason=normalize_finish_reason(value(response, "stop_reason")),
                usage=normalize_usage(value(response, "usage")),
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise translate_provider_exception(exc, self.name) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        client = await self._client()
        try:
            async with client.messages.stream(**self._kwargs(request)) as stream:
                async for text in stream.text_stream:
                    if text:
                        yield StreamEvent(type="delta", delta=text)
                response = await stream.get_final_message()
                yield StreamEvent(
                    type="done",
                    finish_reason=normalize_finish_reason(value(response, "stop_reason")),
                    usage=normalize_usage(value(response, "usage")),
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise translate_provider_exception(exc, self.name) from exc
