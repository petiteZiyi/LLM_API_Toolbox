import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.providers.mock import MockProvider
from app.registry import ProviderRegistry


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        allowed_origins=["http://localhost:3000"],
        request_total_timeout_seconds=5,
        stream_idle_timeout_seconds=2,
        max_retries=0,
        conversation_db_path=":memory:",
    )


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry([MockProvider()])


@pytest.fixture
def client(settings: Settings, registry: ProviderRegistry):
    app = create_app(settings=settings, registry=registry)
    with TestClient(app) as test_client:
        yield test_client
