from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALL = "tool_call"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Message(BaseModel):
    role: Role
    content: Annotated[str, Field(min_length=1)]


class ChatParameters(BaseModel):
    temperature: float | None = Field(default=0.7, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, ge=1)
    web_search_enabled: bool = False


class ChatRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    model: str = Field(min_length=1, max_length=200)
    messages: list[Message] = Field(min_length=1, max_length=50)
    system_prompt: str | None = Field(default=None, max_length=20_000)
    parameters: ChatParameters = Field(default_factory=ChatParameters)

    @model_validator(mode="after")
    def last_message_must_be_user(self) -> "ChatRequest":
        if self.messages[-1].role is not Role.USER:
            raise ValueError("the last message must have role=user")
        return self


class Usage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ChatResult(BaseModel):
    output_text: str
    provider: str
    model: str
    finish_reason: FinishReason = FinishReason.UNKNOWN
    usage: Usage = Field(default_factory=Usage)


class ChatResponse(BaseModel):
    request_id: str
    data: ChatResult


class ErrorDetail(BaseModel):
    code: str
    message: str
    provider: str | None = None
    retryable: bool = False


class ErrorResponse(BaseModel):
    request_id: str
    error: ErrorDetail


class ModelInfo(BaseModel):
    id: str
    display_name: str
    provider: str
    capabilities: list[Literal["text", "streaming"]] = Field(
        default_factory=lambda: ["text", "streaming"]
    )
    default: bool = False
    max_output_tokens: int | None = None


class ProviderStatus(BaseModel):
    name: str
    display_name: str
    status: Literal["available", "unavailable"]
    reason_code: str | None = None
    capabilities: list[Literal["text", "streaming"]] = Field(
        default_factory=lambda: ["text", "streaming"]
    )


class ProviderConfigUpdate(BaseModel):
    api_key: str | None = Field(default=None, max_length=4096)
    clear_api_key: bool = False
    base_url: str = Field(min_length=8, max_length=2048)
    models: list[str] = Field(min_length=1, max_length=20)

    @field_validator("api_key", mode="before")
    @classmethod
    def blank_key_keeps_current(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        allowed_http = normalized.startswith("http://localhost") or normalized.startswith(
            "http://127.0.0.1"
        )
        if not normalized.startswith("https://") and not allowed_http:
            raise ValueError("base_url must use HTTPS, except for localhost")
        return normalized

    @field_validator("models")
    @classmethod
    def normalize_models(cls, value: list[str]) -> list[str]:
        models = list(dict.fromkeys(model.strip() for model in value if model.strip()))
        if not models or any(len(model) > 200 for model in models):
            raise ValueError("at least one valid model is required")
        return models


class ProviderConfigView(BaseModel):
    provider: Literal["openai", "anthropic", "deepseek"]
    display_name: str
    api_key_configured: bool
    base_url: str
    models: list[str]
    persistence: Literal["environment", "runtime"]


class ProviderConnectionTestRequest(BaseModel):
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str = Field(min_length=8, max_length=2048)
    model: str = Field(min_length=1, max_length=200)

    @field_validator("api_key", mode="before")
    @classmethod
    def blank_key_uses_current(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        allowed_http = normalized.startswith("http://localhost") or normalized.startswith(
            "http://127.0.0.1"
        )
        if not normalized.startswith("https://") and not allowed_http:
            raise ValueError("base_url must use HTTPS, except for localhost")
        return normalized

    @field_validator("model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("model is required")
        return normalized


class ProviderConnectionTestResult(BaseModel):
    success: Literal[True] = True
    provider: str
    model: str
    latency_ms: int = Field(ge=0)


class StreamEvent(BaseModel):
    type: Literal["delta", "done"]
    delta: str | None = None
    finish_reason: FinishReason | None = None
    usage: Usage | None = None


class ConversationCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=200)
    system_prompt: str | None = Field(default=None, max_length=20_000)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)
    web_search_enabled: bool = False
    title: str | None = Field(default=None, max_length=120)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    system_prompt: str | None = Field(default=None, max_length=20_000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int | None = Field(default=None, ge=1, le=8192)
    web_search_enabled: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ConversationUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class StoredMessageCreate(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=100_000)
    status: Literal["complete", "cancelled", "error"] = "complete"
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=200)
    finish_reason: str | None = Field(default=None, max_length=64)
    usage: Usage | None = None


class StoredMessage(BaseModel):
    id: str
    conversation_id: str
    role: Role
    content: str
    status: str
    provider: str | None = None
    model: str | None = None
    finish_reason: str | None = None
    usage: Usage | None = None
    created_at: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    provider: str
    model: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationDetail(ConversationSummary):
    system_prompt: str | None = None
    temperature: float
    max_output_tokens: int
    web_search_enabled: bool = False
    messages: list[StoredMessage] = Field(default_factory=list)
