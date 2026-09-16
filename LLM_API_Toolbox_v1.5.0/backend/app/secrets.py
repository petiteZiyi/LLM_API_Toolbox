from typing import Protocol


class SecretStore(Protocol):
    async def get_secret(self, provider: str) -> str | None: ...


class EnvSecretStore:
    def __init__(self, secrets: dict[str, str | None]) -> None:
        self._secrets = secrets.copy()

    async def get_secret(self, provider: str) -> str | None:
        return self._secrets.get(provider)

    def snapshot(self) -> dict[str, str | None]:
        return self._secrets.copy()
