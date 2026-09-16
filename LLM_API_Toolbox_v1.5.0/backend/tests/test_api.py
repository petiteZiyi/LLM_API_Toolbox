import json

from app.domain import ChatResult, FinishReason


def request_body(**overrides):
    body = {
        "provider": "mock",
        "model": "mock-echo-v1",
        "messages": [{"role": "user", "content": "你好"}],
        "system_prompt": "回答简洁",
        "parameters": {"temperature": 0.7, "max_output_tokens": 128},
    }
    body.update(overrides)
    return body


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line[6:].strip() for line in lines if line.startswith("event:"))
        data = next(json.loads(line[5:].strip()) for line in lines if line.startswith("data:"))
        events.append((event, data))
    return events


def test_health_and_provider_discovery(client):
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    providers = client.get("/api/v1/providers").json()["providers"]
    assert providers[0]["name"] == "mock"
    assert providers[0]["status"] == "available"


def test_non_streaming_chat(client):
    response = client.post("/api/v1/chat/completions", json=request_body())
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"].startswith("req_")
    assert "Mock Provider" in body["data"]["output_text"]
    assert body["data"]["finish_reason"] == "stop"
    assert body["data"]["usage"]["total_tokens"] > 0
    assert response.headers["x-request-id"] == body["request_id"]


def test_web_search_flag_enriches_request_before_chat(client, monkeypatch):
    called = {}

    async def enrich(query, system_prompt):
        called.update(query=query, system_prompt=system_prompt)
        return "enriched search context"

    monkeypatch.setattr(client.app.state.chat_service.web_search, "enrich_system_prompt", enrich)
    response = client.post(
        "/api/v1/chat/completions",
        json=request_body(parameters={
            "temperature": 0.7,
            "max_output_tokens": 128,
            "web_search_enabled": True,
        }),
    )
    assert response.status_code == 200
    assert called == {"query": "你好", "system_prompt": "回答简洁"}


def test_streaming_event_state_machine(client):
    with client.stream("POST", "/api/v1/chat/completions/stream", json=request_body()) as response:
        text = "".join(response.iter_text())
    events = parse_sse(text)
    names = [name for name, _ in events]
    assert names[0] == "meta"
    assert names[-1] == "done"
    assert set(names[1:-1]) == {"delta"}
    assert [data["seq"] for _, data in events] == list(range(len(events)))
    assert "Mock Provider" in "".join(data["delta"] for name, data in events if name == "delta")


def test_validation_is_normalized(client):
    response = client.post(
        "/api/v1/chat/completions",
        json=request_body(messages=[{"role": "assistant", "content": "not allowed last"}]),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_model_is_rejected_before_provider_call(client):
    response = client.post(
        "/api/v1/chat/completions", json=request_body(model="not-a-model")
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MODEL_NOT_FOUND"


def test_runtime_provider_configuration_never_returns_secret(client):
    before = client.get("/api/v1/settings/providers")
    assert before.status_code == 200
    openai = next(item for item in before.json()["providers"] if item["provider"] == "openai")
    assert openai["api_key_configured"] is False

    secret = "sk-test-do-not-return"
    response = client.put(
        "/api/v1/settings/providers/openai",
        json={
            "api_key": secret,
            "clear_api_key": False,
            "base_url": "https://example.test/v1",
            "models": ["test-model", "test-model"],
        },
    )
    assert response.status_code == 200
    assert secret not in response.text
    assert response.json()["provider"]["api_key_configured"] is True
    assert response.json()["provider"]["models"] == ["test-model"]

    providers = client.get("/api/v1/providers").json()["providers"]
    assert next(item for item in providers if item["name"] == "openai")["status"] == "available"
    assert client.get("/api/v1/models?provider=openai").json()["models"][0]["id"] == "test-model"


def test_runtime_provider_configuration_rejects_insecure_remote_url(client):
    response = client.put(
        "/api/v1/settings/providers/openai",
        json={
            "base_url": "http://example.com/v1",
            "models": ["test-model"],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_provider_connection_uses_unsaved_form_without_returning_secret(client, monkeypatch):
    class SuccessfulProvider:
        async def chat(self, request):
            assert request.model == "model-under-test"
            return ChatResult(
                output_text="OK",
                provider="openai",
                model=request.model,
                finish_reason=FinishReason.STOP,
            )

    captured = {}

    def build_test_provider(provider, api_key, base_url, model):
        captured.update(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        return SuccessfulProvider()

    monkeypatch.setattr(
        client.app.state.runtime_config,
        "build_test_provider",
        build_test_provider,
    )
    secret = "sk-unsaved-test-secret"
    response = client.post(
        "/api/v1/settings/providers/openai/test",
        json={
            "api_key": secret,
            "base_url": "https://example.test/v1",
            "model": "model-under-test",
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["model"] == "model-under-test"
    assert response.json()["latency_ms"] >= 0
    assert captured["api_key"] == secret
    assert secret not in response.text
    settings = client.get("/api/v1/settings/providers").json()["providers"]
    assert next(item for item in settings if item["provider"] == "openai")["api_key_configured"] is False


def test_provider_connection_requires_existing_or_temporary_key(client):
    response = client.post(
        "/api/v1/settings/providers/openai/test",
        json={
            "api_key": None,
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-5-mini",
        },
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_NOT_CONFIGURED"


def test_application_meta_exposes_compatibility_version(client):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    assert response.json()["version"] == "1.5.0"
    assert response.json()["api_compatibility_version"] == "1.5"


def test_cors_allows_browser_conversation_updates(client):
    response = client.options(
        "/api/v1/conversations/conv_test",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    allowed_methods = response.headers["access-control-allow-methods"]
    assert "PATCH" in allowed_methods
    assert "DELETE" in allowed_methods


def test_conversation_history_crud_and_search(client):
    created = client.post(
        "/api/v1/conversations",
        json={
            "provider": "mock",
            "model": "mock-echo-v1",
            "system_prompt": "简洁回答",
            "temperature": 0.5,
            "max_output_tokens": 512,
        },
    )
    assert created.status_code == 201
    conversation_id = created.json()["conversation"]["id"]

    first_message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"role": "user", "content": "解释一下混合检索的原理"},
    )
    assert first_message.status_code == 201
    assistant_message = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={
            "role": "assistant",
            "content": "混合检索结合关键词与向量检索。",
            "provider": "mock",
            "model": "mock-echo-v1",
            "usage": {"input_tokens": 6, "output_tokens": 8, "total_tokens": 14},
        },
    )
    assert assistant_message.status_code == 201

    detail = client.get(f"/api/v1/conversations/{conversation_id}").json()["conversation"]
    assert detail["title"].startswith("解释一下混合检索")
    assert len(detail["messages"]) == 2
    assert detail["messages"][1]["usage"]["total_tokens"] == 14

    search = client.get("/api/v1/conversations", params={"query": "关键词"}).json()
    assert search["conversations"][0]["id"] == conversation_id

    renamed = client.patch(
        f"/api/v1/conversations/{conversation_id}", json={"title": "RAG 检索讨论"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["conversation"]["title"] == "RAG 检索讨论"

    deleted = client.delete(f"/api/v1/conversations/{conversation_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
