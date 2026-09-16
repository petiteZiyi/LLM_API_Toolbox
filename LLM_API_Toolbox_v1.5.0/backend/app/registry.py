from app.domain import ModelInfo, ProviderStatus
from app.errors import model_not_found, provider_not_found
from app.providers.base import BaseProvider


class ProviderRegistry:
    def __init__(self, providers: list[BaseProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def get(self, name: str) -> BaseProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise provider_not_found(name)
        return provider

    async def statuses(self) -> list[ProviderStatus]:
        return [await provider.get_status() for provider in self._providers.values()]

    async def models(self, provider_name: str) -> list[ModelInfo]:
        return await self.get(provider_name).list_models()

    async def validate_model(self, provider_name: str, model: str) -> BaseProvider:
        provider = self.get(provider_name)
        models = await provider.list_models()
        if model not in {item.id for item in models}:
            raise model_not_found(provider_name, model)
        return provider

