import asyncio
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.domain import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationUpdate,
    ErrorDetail,
    ProviderConfigUpdate,
    ProviderConnectionTestRequest,
    ProviderConnectionTestResult,
    StoredMessageCreate,
    StreamEvent,
)
from app.errors import AppError, ProviderError
from app.registry import ProviderRegistry
from app.service import ChatService

router = APIRouter(prefix="/api/v1")
APP_VERSION = "1.5.0"
API_COMPATIBILITY_VERSION = "1.5"


def get_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_registry(request: Request) -> ProviderRegistry:
    return request.app.state.registry


def get_runtime_config(request: Request):
    return request.app.state.runtime_config


def encode_sse(event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode()


@router.post("/chat/completions", response_model=ChatResponse)
async def chat_completion(
    payload: ChatRequest,
    request: Request,
    service: ChatService = Depends(get_service),
) -> ChatResponse:
    try:
        result = await service.chat(payload)
    except TimeoutError as exc:
        raise ProviderError(
            "PROVIDER_TIMEOUT",
            "Provider request timed out.",
            504,
            payload.provider,
            True,
        ) from exc
    return ChatResponse(request_id=request.state.request_id, data=result)


@router.post("/chat/completions/stream")
async def stream_chat_completion(
    payload: ChatRequest,
    request: Request,
    service: ChatService = Depends(get_service),
) -> StreamingResponse:
    provider = await service.prepare(payload)
    request_id = request.state.request_id

    async def body() -> AsyncIterator[bytes]:
        seq = 0
        yield encode_sse(
            "meta",
            {
                "request_id": request_id,
                "provider": payload.provider,
                "model": payload.model,
                "seq": seq,
            },
        )
        seq += 1
        try:
            async for event in service.stream(payload, provider):
                if await request.is_disconnected():
                    return
                if event.type == "delta":
                    yield encode_sse("delta", {"delta": event.delta or "", "seq": seq})
                else:
                    yield encode_sse(
                        "done",
                        {
                            "finish_reason": event.finish_reason,
                            "usage": event.usage.model_dump() if event.usage else None,
                            "seq": seq,
                        },
                    )
                seq += 1
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            error = ErrorDetail(
                code="PROVIDER_TIMEOUT",
                message="Provider request timed out.",
                provider=payload.provider,
                retryable=True,
            )
            yield encode_sse("error", {"error": error.model_dump(), "seq": seq})
        except AppError as exc:
            error = ErrorDetail(
                code=exc.code,
                message=exc.message,
                provider=exc.provider,
                retryable=exc.retryable,
            )
            yield encode_sse("error", {"error": error.model_dump(), "seq": seq})

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/providers")
async def list_providers(registry: ProviderRegistry = Depends(get_registry)) -> dict:
    return {"providers": [item.model_dump() for item in await registry.statuses()]}


@router.get("/models")
async def list_models(
    provider: str = Query(min_length=1, max_length=64),
    registry: ProviderRegistry = Depends(get_registry),
) -> dict:
    return {"models": [item.model_dump() for item in await registry.models(provider)]}


@router.get("/settings/providers")
async def list_provider_settings(request: Request) -> dict:
    return {
        "providers": [item.model_dump() for item in request.app.state.runtime_config.views()],
        "notice": "Runtime API keys are kept in backend memory and are never returned.",
    }


@router.put("/settings/providers/{provider}")
async def update_provider_settings(
    provider: str,
    payload: ProviderConfigUpdate,
    request: Request,
) -> dict:
    try:
        view = await request.app.state.runtime_config.update(provider, payload)
    except KeyError as exc:
        raise AppError("PROVIDER_NOT_FOUND", "Provider does not exist.", 404) from exc

    # Atomic reference replacement lets in-flight requests finish on the old registry.
    new_registry = request.app.state.runtime_config.build_registry()
    request.app.state.registry = new_registry
    request.app.state.chat_service = ChatService(new_registry, request.app.state.settings)
    return {"provider": view.model_dump()}


@router.post(
    "/settings/providers/{provider}/test",
    response_model=ProviderConnectionTestResult,
)
async def test_provider_connection(
    provider: str,
    payload: ProviderConnectionTestRequest,
    request: Request,
) -> ProviderConnectionTestResult:
    try:
        test_provider = request.app.state.runtime_config.build_test_provider(
            provider,
            payload.api_key,
            payload.base_url,
            payload.model,
        )
    except KeyError as exc:
        raise AppError("PROVIDER_NOT_FOUND", "Provider does not exist.", 404) from exc

    test_request = ChatRequest(
        provider=provider,
        model=payload.model,
        messages=[{"role": "user", "content": "Reply with OK."}],
        parameters={"temperature": None, "max_output_tokens": 16},
    )
    started = time.perf_counter()
    try:
        async with asyncio.timeout(request.app.state.settings.request_total_timeout_seconds):
            result = await test_provider.chat(test_request)
    except TimeoutError as exc:
        raise ProviderError(
            "PROVIDER_TIMEOUT",
            "Provider request timed out.",
            504,
            provider,
            True,
        ) from exc
    return ProviderConnectionTestResult(
        provider=provider,
        model=result.model or payload.model,
        latency_ms=round((time.perf_counter() - started) * 1000),
    )


@router.get("/meta")
async def application_meta() -> dict:
    return {
        "name": "LLM API Toolbox",
        "version": APP_VERSION,
        "api_compatibility_version": API_COMPATIBILITY_VERSION,
    }


def conversation_not_found(conversation_id: str) -> AppError:
    return AppError(
        "CONVERSATION_NOT_FOUND",
        f"Conversation '{conversation_id}' does not exist.",
        404,
    )


@router.get("/conversations")
async def list_conversations(
    request: Request,
    query: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict:
    items = request.app.state.conversation_store.list(query=query, limit=limit)
    return {"conversations": [item.model_dump() for item in items]}


@router.post("/conversations", status_code=201)
async def create_conversation(payload: ConversationCreate, request: Request) -> dict:
    conversation = request.app.state.conversation_store.create(payload)
    return {"conversation": conversation.model_dump()}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, request: Request) -> dict:
    try:
        conversation = request.app.state.conversation_store.get(conversation_id)
    except KeyError as exc:
        raise conversation_not_found(conversation_id) from exc
    return {"conversation": conversation.model_dump()}


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    request: Request,
) -> dict:
    try:
        conversation = request.app.state.conversation_store.update(conversation_id, payload)
    except KeyError as exc:
        raise conversation_not_found(conversation_id) from exc
    return {"conversation": conversation.model_dump()}


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, request: Request) -> None:
    try:
        request.app.state.conversation_store.delete(conversation_id)
    except KeyError as exc:
        raise conversation_not_found(conversation_id) from exc


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def append_conversation_message(
    conversation_id: str,
    payload: StoredMessageCreate,
    request: Request,
) -> dict:
    try:
        message = request.app.state.conversation_store.add_message(conversation_id, payload)
    except KeyError as exc:
        raise conversation_not_found(conversation_id) from exc
    return {"message": message.model_dump()}


@router.get("/health/live")
async def health_live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(registry: ProviderRegistry = Depends(get_registry)) -> dict:
    statuses = await registry.statuses()
    mock_ready = any(item.name == "mock" and item.status == "available" for item in statuses)
    if not mock_ready:
        raise AppError("NOT_READY", "Mock provider is not ready.", 503)
    return {"status": "ready", "providers": [item.model_dump() for item in statuses]}
