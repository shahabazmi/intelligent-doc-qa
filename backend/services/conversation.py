from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from .database import get_connection

logger = logging.getLogger(__name__)


def _ensure_schema():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            sources_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
    """)
    # Migration: add title column to existing tables that lack it
    cols = {r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()}
    if "title" not in cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN title TEXT NOT NULL DEFAULT ''")
        conn.commit()


def start_conversation(title: str = "") -> str:
    _ensure_schema()
    cid = uuid.uuid4().hex
    get_connection().execute("INSERT INTO conversations (id, title) VALUES (?, ?)", (cid, title))
    get_connection().commit()
    return cid


def rename_conversation(conversation_id: str, title: str) -> None:
    _ensure_schema()
    get_connection().execute("UPDATE conversations SET title=? WHERE id=?", (title, conversation_id))
    get_connection().commit()


def append(conversation_id: str, role: str, content: str, sources: Optional[list[dict]] = None) -> None:
    _ensure_schema()
    get_connection().execute(
        "INSERT INTO messages (conversation_id, role, content, sources_json) VALUES (?,?,?,?)",
        (conversation_id, role, content, json.dumps(sources or [])),
    )
    get_connection().commit()


def recent_turns(conversation_id: str, n: int = 6) -> list[dict]:
    _ensure_schema()
    rows = get_connection().execute(
        "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    turns = [{"role": r["role"], "content": r["content"]} for r in rows]
    return turns[-(n * 2):] if n else turns


def list_conversations() -> list[dict]:
    _ensure_schema()
    rows = get_connection().execute(
        "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC"
    ).fetchall()
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    _ensure_schema()
    conv = get_connection().execute(
        "SELECT id, title, created_at FROM conversations WHERE id=?", (conversation_id,)
    ).fetchone()
    if not conv:
        return None
    messages = get_connection().execute(
        "SELECT role, content, sources_json FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    return {
        "id": conv["id"],
        "title": conv["title"],
        "created_at": conv["created_at"],
        "messages": [
            {"role": m["role"], "content": m["content"], "sources": json.loads(m["sources_json"] or "[]")}
            for m in messages
        ],
    }


def delete_conversation(conversation_id: str) -> None:
    _ensure_schema()
    get_connection().execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
    get_connection().commit()
