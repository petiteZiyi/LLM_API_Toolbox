from functools import lru_cache

from app.config import get_settings
from app.registry import ProviderRegistry
from app.runtime_config import RuntimeConfigManager
from app.service import ChatService


@lru_cache
def get_registry() -> ProviderRegistry:
    return RuntimeConfigManager(get_settings()).build_registry()


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(get_registry(), get_settings())
