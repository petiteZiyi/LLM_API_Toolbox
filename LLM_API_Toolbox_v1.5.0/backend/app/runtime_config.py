import asyncio

from app.config import Settings
from app.domain import ProviderConfigUpdate, ProviderConfigView
from app.providers import AnthropicProvider, MockProvider, OpenAICompatibleProvider, OpenAIProvider
from app.registry import ProviderRegistry
from app.secrets import EnvSecretStore


DISPLAY_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
}


class RuntimeConfigManager:
    """Owns local runtime credentials without ever exposing their values."""

    def __init__(self, settings: Settings) -> None:
        self._lock = asyncio.Lock()
        self._environment_keys = {
            "openai": settings.openai_api_key,
            "anthropic": settings.anthropic_api_key,
            "deepseek": settings.deepseek_api_key,
        }
        self._keys = self._environment_keys.copy()
        self._base_urls = {
            "openai": settings.openai_base_url,
            "anthropic": settings.anthropic_base_url,
            "deepseek": settings.deepseek_base_url,
        }
        self._models = {
            "openai": settings.openai_models.copy(),
            "anthropic": settings.anthropic_models.copy(),
            "deepseek": settings.deepseek_models.copy(),
        }
        self._runtime_changed = set()

    @staticmethod
    def _provider(provider: str, key: str | None, base_url: str, models: list[str]):
        secret_store = EnvSecretStore({provider: key})
        if provider == "openai":
            return OpenAIProvider(secret_store, models, base_url=base_url)
        if provider == "anthropic":
            return AnthropicProvider(secret_store, models, base_url=base_url)
        if provider == "deepseek":
            return OpenAICompatibleProvider(
                name="deepseek",
                display_name="DeepSeek",
                base_url=base_url,
                secret_store=secret_store,
                models=models,
            )
        raise KeyError(provider)

    def build_registry(self) -> ProviderRegistry:
        providers = [MockProvider()]
        providers.extend(
            self._provider(
                provider,
                self._keys[provider],
                self._base_urls[provider],
                self._models[provider],
            )
            for provider in DISPLAY_NAMES
        )
        return ProviderRegistry(providers)

    def build_test_provider(
        self,
        provider: str,
        api_key: str | None,
        base_url: str,
        model: str,
    ):
        if provider not in DISPLAY_NAMES:
            raise KeyError(provider)
        effective_key = api_key.strip() if api_key is not None else self._keys[provider]
        return self._provider(provider, effective_key, base_url, [model])

    def views(self) -> list[ProviderConfigView]:
        return [self.view(provider) for provider in DISPLAY_NAMES]

    def view(self, provider: str) -> ProviderConfigView:
        return ProviderConfigView(
            provider=provider,
            display_name=DISPLAY_NAMES[provider],
            api_key_configured=bool(self._keys[provider]),
            base_url=self._base_urls[provider],
            models=self._models[provider],
            persistence="runtime" if provider in self._runtime_changed else "environment",
        )

    async def update(self, provider: str, payload: ProviderConfigUpdate) -> ProviderConfigView:
        if provider not in DISPLAY_NAMES:
            raise KeyError(provider)
        async with self._lock:
            if payload.clear_api_key:
                self._keys[provider] = None
            elif payload.api_key is not None:
                self._keys[provider] = payload.api_key.strip()
            self._base_urls[provider] = payload.base_url
            self._models[provider] = payload.models.copy()
            self._runtime_changed.add(provider)
            return self.view(provider)
