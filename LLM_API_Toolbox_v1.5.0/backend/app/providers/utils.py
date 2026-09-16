from typing import Any

from app.domain import FinishReason, Usage
from app.errors import ProviderError


def value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def normalize_usage(raw: Any) -> Usage:
    if raw is None:
        return Usage()
    input_tokens = value(raw, "input_tokens", value(raw, "prompt_tokens"))
    output_tokens = value(raw, "output_tokens", value(raw, "completion_tokens"))
    total_tokens = value(raw, "total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def normalize_finish_reason(reason: str | None) -> FinishReason:
    mapping = {
        "stop": FinishReason.STOP,
        "completed": FinishReason.STOP,
        "end_turn": FinishReason.STOP,
        "stop_sequence": FinishReason.STOP,
        "length": FinishReason.LENGTH,
        "max_tokens": FinishReason.LENGTH,
        "max_output_tokens": FinishReason.LENGTH,
        "content_filter": FinishReason.CONTENT_FILTER,
        "refusal": FinishReason.CONTENT_FILTER,
        "tool_calls": FinishReason.TOOL_CALL,
        "tool_use": FinishReason.TOOL_CALL,
    }
    return mapping.get(reason or "", FinishReason.UNKNOWN)


def translate_provider_exception(exc: Exception, provider: str) -> ProviderError:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)

    if status in {401, 403} or "authentication" in name or "permission" in name:
        return ProviderError(
            "PROVIDER_AUTH_FAILED",
            "Provider authentication failed.",
            502,
            provider,
            False,
        )
    if status == 429 or "ratelimit" in name or "rate_limit" in name:
        return ProviderError(
            "RATE_LIMITED", "Provider rate limit reached.", 429, provider, True
        )
    if status == 402:
        return ProviderError(
            "PROVIDER_PAYMENT_REQUIRED",
            "Provider account has insufficient balance or requires payment.",
            402,
            provider,
            False,
        )
    if "timeout" in name:
        return ProviderError(
            "PROVIDER_TIMEOUT", "Provider request timed out.", 504, provider, True
        )
    if status is not None and 400 <= status < 500:
        return ProviderError(
            "PROVIDER_INVALID_REQUEST",
            "Provider rejected the request.",
            502,
            provider,
            False,
        )
    return ProviderError(
        "PROVIDER_UPSTREAM_ERROR",
        "Provider returned an unavailable or invalid response.",
        502,
        provider,
        True,
    )
