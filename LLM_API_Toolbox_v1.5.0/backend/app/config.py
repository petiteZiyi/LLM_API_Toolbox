from functools import lru_cache

from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None

    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com"
    deepseek_base_url: str = "https://api.deepseek.com"

    openai_models: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["gpt-5-mini"]
    )
    anthropic_models: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["claude-sonnet-4-5"]
    )
    deepseek_models: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["deepseek-flash", "deepseek-v4-pro"]
    )

    default_provider: str = "mock"
    conversation_db_path: str = "../data/llm_toolbox.db"
    request_total_timeout_seconds: float = Field(default=60, gt=0)
    stream_idle_timeout_seconds: float = Field(default=30, gt=0)
    max_concurrent_requests: int = Field(default=20, ge=1, le=1000)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_messages: int = Field(default=50, ge=1, le=500)
    max_message_chars: int = Field(default=50_000, ge=1)
    max_total_message_chars: int = Field(default=100_000, ge=1)
    max_output_tokens_limit: int = Field(default=8192, ge=1)
    web_search_timeout_seconds: float = Field(default=8, gt=0, le=30)
    web_search_max_results: int = Field(default=5, ge=1, le=10)

    @field_validator(
        "allowed_origins", "openai_models", "anthropic_models", "deepseek_models",
        mode="before",
    )
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("openai_api_key", "anthropic_api_key", "deepseek_api_key", mode="before")
    @classmethod
    def blank_secret_is_none(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
