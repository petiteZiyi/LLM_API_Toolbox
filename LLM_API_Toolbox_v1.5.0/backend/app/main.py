import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.config import Settings, get_settings
from app.conversations import ConversationStore
from app.dependencies import get_chat_service, get_registry
from app.domain import ErrorDetail, ErrorResponse
from app.errors import AppError
from app.logging_config import configure_logging
from app.runtime_config import RuntimeConfigManager

logger = logging.getLogger("llm_toolbox")


def error_body(request_id: str, error: ErrorDetail) -> dict:
    return ErrorResponse(request_id=request_id, error=error).model_dump()


def create_app(settings: Settings | None = None, registry=None) -> FastAPI:
    selected_settings = settings or get_settings()
    configure_logging(selected_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime_config = RuntimeConfigManager(selected_settings)
        app.state.registry = registry or app.state.runtime_config.build_registry()
        app.state.chat_service = ChatServiceFactory(app.state.registry, selected_settings)
        app.state.settings = selected_settings
        app.state.conversation_store = ConversationStore(selected_settings.conversation_db_path)
        try:
            yield
        finally:
            app.state.conversation_store.close()

    app = FastAPI(
        title="LLM API Toolbox",
        version="1.5.0",
        description="Unified local API for OpenAI, Anthropic, DeepSeek and Mock providers.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=selected_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        raw_request_id = request.headers.get("X-Request-ID", "")
        request_id = raw_request_id if raw_request_id.startswith("req_") else f"req_{uuid.uuid4().hex}"
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "status_code": response.status_code,
            },
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                request.state.request_id,
                ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    provider=exc.provider,
                    retryable=exc.retryable,
                ),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_body(
                request.state.request_id,
                ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request validation failed.",
                    retryable=False,
                ),
            ),
        )

    app.include_router(router)
    return app


def ChatServiceFactory(registry, settings):
    from app.service import ChatService

    return ChatService(registry, settings)


app = create_app()
