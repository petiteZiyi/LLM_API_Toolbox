from collections.abc import AsyncIterator, Callable
from typing import Any

from openai import AsyncOpenAI

from app.domain import ChatRequest, ChatResult, ModelInfo, ProviderStatus, StreamEvent, Usage
from app.errors import ProviderError, not_configured
from app.providers.utils import normalize_finish_reason, normalize_usage, translate_provider_exception, value
from app.secrets import SecretStore


class OpenAICompatibleProvider:
    def __init__(
        self,
        name: str,
        display_name: str,
        base_url: str,
        secret_store: SecretStore,
        models: list[str],
        client_factory: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.base_url = base_url
        self.secret_store = secret_store
        self.models = models
        self.client_factory = client_factory or (
            lambda key, url: AsyncOpenAI(api_key=key, base_url=url, max_retries=0)
        )

    async def _client(self) -> Any:
        key = await self.secret_store.get_secret(self.name)
        if not key:
            raise not_configured(self.name)
        return self.client_factory(key, self.base_url)

    async def get_status(self) -> ProviderStatus:
        available = bool(await self.secret_store.get_secret(self.name))
        return ProviderStatus(
            name=self.name,
            display_name=self.display_name,
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
        messages = [message.model_dump(mode="json") for message in request.messages]
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.parameters.max_output_tokens,
        }
        if request.parameters.temperature is not None:
            kwargs["temperature"] = request.parameters.temperature
        return kwargs

    async def chat(self, request: ChatRequest) -> ChatResult:
        client = await self._client()
        try:
            response = await client.chat.completions.create(**self._kwargs(request))
            choice = response.choices[0]
            return ChatResult(
                output_text=value(value(choice, "message"), "content", "") or "",
                provider=self.name,
                model=value(response, "model", request.model),
                finish_reason=normalize_finish_reason(value(choice, "finish_reason")),
                usage=normalize_usage(value(response, "usage")),
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise translate_provider_exception(exc, self.name) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        client = await self._client()
        finish_reason = None
        final_usage = Usage()
        try:
            stream = await client.chat.completions.create(
                **self._kwargs(request),
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                usage = value(chunk, "usage")
                if usage is not None:
                    final_usage = normalize_usage(usage)
                choices = value(chunk, "choices", []) or []
                if not choices:
                    continue
                choice = choices[0]
                delta = value(value(choice, "delta"), "content", "") or ""
                if delta:
                    yield StreamEvent(type="delta", delta=delta)
                finish_reason = value(choice, "finish_reason", finish_reason)
            yield StreamEvent(
                type="done",
                finish_reason=normalize_finish_reason(finish_reason),
                usage=final_usage,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise translate_provider_exception(exc, self.name) from exc

