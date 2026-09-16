import sqlite3

from app.conversations import ConversationStore
from app.domain import ConversationCreate, ConversationUpdate, StoredMessageCreate


def test_sqlite_history_survives_store_restart(tmp_path):
    database = tmp_path / "history.db"
    store = ConversationStore(str(database))
    conversation = store.create(
        ConversationCreate(provider="mock", model="mock-echo-v1")
    )
    store.add_message(
        conversation.id,
        StoredMessageCreate(role="user", content="持久化测试"),
    )
    store.update(
        conversation.id,
        ConversationUpdate(
            provider="openai",
            model="gpt-test",
            system_prompt="新的系统提示词",
            temperature=0.2,
            max_output_tokens=256,
            web_search_enabled=True,
        ),
    )
    store.close()

    reopened = ConversationStore(str(database))
    restored = reopened.get(conversation.id)
    assert restored.title == "持久化测试"
    assert restored.provider == "openai"
    assert restored.model == "gpt-test"
    assert restored.system_prompt == "新的系统提示词"
    assert restored.temperature == 0.2
    assert restored.max_output_tokens == 256
    assert restored.web_search_enabled is True
    assert restored.messages[0].content == "持久化测试"
    reopened.close()


def test_existing_v14_database_is_migrated_with_search_disabled(tmp_path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, provider TEXT NOT NULL,
            model TEXT NOT NULL, system_prompt TEXT, temperature REAL NOT NULL,
            max_output_tokens INTEGER NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO conversations VALUES
            ('conv_old', '旧会话', 'mock', 'mock-echo-v1', NULL, 0.7, 128,
             '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
        """
    )
    connection.commit()
    connection.close()

    store = ConversationStore(str(database))
    assert store.get("conv_old").web_search_enabled is False
    store.close()
