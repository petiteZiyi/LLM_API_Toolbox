from collections.abc import AsyncIterator, Callable
from typing import Any

from openai import AsyncOpenAI

from app.domain import (
    ChatRequest,
    ChatResult,
    FinishReason,
    ModelInfo,
    ProviderStatus,
    StreamEvent,
)
from app.errors import ProviderError, not_configured
from app.providers.utils import normalize_finish_reason, normalize_usage, translate_provider_exception, value
from app.secrets import SecretStore


class OpenAIProvider:
    name = "openai"

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
            lambda key: AsyncOpenAI(api_key=key, base_url=base_url, max_retries=0)
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
            display_name="OpenAI",
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
            "input": [message.model_dump(mode="json") for message in request.messages],
            "max_output_tokens": request.parameters.max_output_tokens,
        }
        if request.system_prompt:
            kwargs["instructions"] = request.system_prompt
        if request.parameters.temperature is not None:
            kwargs["temperature"] = request.parameters.temperature
        return kwargs

    async def chat(self, request: ChatRequest) -> ChatResult:
        client = await self._client()
        try:
            response = await client.responses.create(**self._kwargs(request))
            status = value(response, "status")
            reason = status
            incomplete = value(response, "incomplete_details")
            if incomplete is not None:
                reason = value(incomplete, "reason", reason)
            return ChatResult(
                output_text=value(response, "output_text", "") or "",
                provider=self.name,
                model=value(response, "model", request.model),
                finish_reason=normalize_finish_reason(reason),
                usage=normalize_usage(value(response, "usage")),
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise translate_provider_exception(exc, self.name) from exc

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamEvent]:
        client = await self._client()
        completed = False
        try:
            stream = await client.responses.create(**self._kwargs(request), stream=True)
            async for event in stream:
                event_type = value(event, "type", "")
                if event_type in {"response.output_text.delta", "response.refusal.delta"}:
                    delta = value(event, "delta", "") or ""
                    if delta:
                        yield StreamEvent(type="delta", delta=delta)
                elif event_type == "response.completed":
                    response = value(event, "response")
                    yield StreamEvent(
                        type="done",
                        finish_reason=FinishReason.STOP,
                        usage=normalize_usage(value(response, "usage")),
                    )
                    completed = True
                elif event_type in {"response.failed", "error"}:
                    raise ProviderError(
                        "PROVIDER_UPSTREAM_ERROR",
                        "OpenAI streaming response failed.",
                        502,
                        self.name,
                        True,
                    )
            if not completed:
                raise ProviderError(
                    "PROVIDER_UPSTREAM_ERROR",
                    "OpenAI stream ended without a completion event.",
                    502,
                    self.name,
                    True,
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise translate_provider_exception(exc, self.name) from exc
