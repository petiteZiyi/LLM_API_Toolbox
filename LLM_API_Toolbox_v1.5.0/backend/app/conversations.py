import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.domain import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    ConversationUpdate,
    StoredMessage,
    StoredMessageCreate,
    Usage,
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class ConversationStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    system_prompt TEXT,
                    temperature REAL NOT NULL,
                    max_output_tokens INTEGER NOT NULL,
                    web_search_enabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    finish_reason TEXT,
                    usage_input INTEGER,
                    usage_output INTEGER,
                    usage_total INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at);
                """
            )
            columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(conversations)")
            }
            if "web_search_enabled" not in columns:
                self._connection.execute(
                    "ALTER TABLE conversations ADD COLUMN web_search_enabled INTEGER NOT NULL DEFAULT 0"
                )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def create(self, payload: ConversationCreate) -> ConversationDetail:
        conversation_id = f"conv_{uuid.uuid4().hex}"
        timestamp = now_iso()
        title = (payload.title or "新对话").strip() or "新对话"
        with self._lock, self._connection:
            self._connection.execute(
                """INSERT INTO conversations
                (id, title, provider, model, system_prompt, temperature, max_output_tokens,
                 web_search_enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    conversation_id,
                    title[:120],
                    payload.provider,
                    payload.model,
                    payload.system_prompt,
                    payload.temperature,
                    payload.max_output_tokens,
                    int(payload.web_search_enabled),
                    timestamp,
                    timestamp,
                ),
            )
        return self.get(conversation_id)

    def list(self, query: str | None = None, limit: int = 100) -> list[ConversationSummary]:
        parameters: list[object] = []
        where = ""
        if query:
            where = "WHERE c.title LIKE ? OR EXISTS (SELECT 1 FROM messages m2 WHERE m2.conversation_id = c.id AND m2.content LIKE ?)"
            pattern = f"%{query.strip()}%"
            parameters.extend([pattern, pattern])
        parameters.append(limit)
        with self._lock:
            rows = self._connection.execute(
                f"""SELECT c.*, COUNT(m.id) AS message_count
                FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id
                {where}
                GROUP BY c.id ORDER BY c.updated_at DESC LIMIT ?""",
                parameters,
            ).fetchall()
        return [self._summary(row) for row in rows]

    def get(self, conversation_id: str) -> ConversationDetail:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row is None:
                raise KeyError(conversation_id)
            messages = self._connection.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at, rowid",
                (conversation_id,),
            ).fetchall()
        return ConversationDetail(
            **self._summary(row, len(messages)).model_dump(),
            system_prompt=row["system_prompt"],
            temperature=row["temperature"],
            max_output_tokens=row["max_output_tokens"],
            web_search_enabled=bool(row["web_search_enabled"]),
            messages=[self._message(item) for item in messages],
        )

    def update(self, conversation_id: str, payload: ConversationUpdate) -> ConversationDetail:
        values = payload.model_dump(exclude_unset=True)
        if "title" in values and values["title"] is not None:
            values["title"] = values["title"].strip()[:120]
        assignments = [f"{field} = ?" for field in values]
        parameters = list(values.values())
        assignments.append("updated_at = ?")
        parameters.extend([now_iso(), conversation_id])
        with self._lock, self._connection:
            cursor = self._connection.execute(
                f"UPDATE conversations SET {', '.join(assignments)} WHERE id = ?",
                parameters,
            )
            if cursor.rowcount == 0:
                raise KeyError(conversation_id)
        return self.get(conversation_id)

    def delete(self, conversation_id: str) -> None:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )
            if cursor.rowcount == 0:
                raise KeyError(conversation_id)

    def add_message(self, conversation_id: str, payload: StoredMessageCreate) -> StoredMessage:
        message_id = f"msg_{uuid.uuid4().hex}"
        timestamp = now_iso()
        usage = payload.usage or Usage()
        with self._lock, self._connection:
            exists = self._connection.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(conversation_id)
            self._connection.execute(
                """INSERT INTO messages
                (id, conversation_id, role, content, status, provider, model, finish_reason,
                 usage_input, usage_output, usage_total, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    message_id,
                    conversation_id,
                    payload.role.value,
                    payload.content,
                    payload.status,
                    payload.provider,
                    payload.model,
                    payload.finish_reason,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.total_tokens,
                    timestamp,
                ),
            )
            title_row = self._connection.execute(
                "SELECT title FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if payload.role.value == "user" and title_row["title"] == "新对话":
                generated = " ".join(payload.content.strip().split())[:36] or "新对话"
                self._connection.execute(
                    "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                    (generated, timestamp, conversation_id),
                )
            else:
                self._connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (timestamp, conversation_id),
                )
        return self._message(
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "role": payload.role.value,
                "content": payload.content,
                "status": payload.status,
                "provider": payload.provider,
                "model": payload.model,
                "finish_reason": payload.finish_reason,
                "usage_input": usage.input_tokens,
                "usage_output": usage.output_tokens,
                "usage_total": usage.total_tokens,
                "created_at": timestamp,
            }
        )

    @staticmethod
    def _summary(row: sqlite3.Row, message_count: int | None = None) -> ConversationSummary:
        count = message_count if message_count is not None else row["message_count"]
        return ConversationSummary(
            id=row["id"], title=row["title"], provider=row["provider"], model=row["model"],
            created_at=row["created_at"], updated_at=row["updated_at"], message_count=count,
        )

    @staticmethod
    def _message(row) -> StoredMessage:
        usage_values = (row["usage_input"], row["usage_output"], row["usage_total"])
        usage = None if all(value is None for value in usage_values) else Usage(
            input_tokens=usage_values[0], output_tokens=usage_values[1], total_tokens=usage_values[2]
        )
        return StoredMessage(
            id=row["id"], conversation_id=row["conversation_id"], role=row["role"],
            content=row["content"], status=row["status"], provider=row["provider"],
            model=row["model"], finish_reason=row["finish_reason"], usage=usage,
            created_at=row["created_at"],
        )
