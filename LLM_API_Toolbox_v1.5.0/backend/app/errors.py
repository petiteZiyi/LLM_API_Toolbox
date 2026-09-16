from dataclasses import dataclass


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int
    provider: str | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class ProviderError(AppError):
    pass


def not_configured(provider: str) -> ProviderError:
    return ProviderError(
        code="PROVIDER_NOT_CONFIGURED",
        message=f"Provider '{provider}' is not configured.",
        status_code=503,
        provider=provider,
        retryable=False,
    )


def provider_not_found(provider: str) -> AppError:
    return AppError(
        code="PROVIDER_NOT_FOUND",
        message=f"Provider '{provider}' was not found.",
        status_code=404,
        provider=provider,
    )


def model_not_found(provider: str, model: str) -> AppError:
    return AppError(
        code="MODEL_NOT_FOUND",
        message=f"Model '{model}' is not configured for provider '{provider}'.",
        status_code=404,
        provider=provider,
    )

