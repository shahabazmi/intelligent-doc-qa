from __future__ import annotations

import json
import logging
import os

from langchain_core.documents import Document

from ..config import MILVUS_DB_URI, UPLOAD_DIR
from .database import get_connection
from .vectordb import reset_vector_store

logger = logging.getLogger(__name__)


def _milvus_lock_path() -> str:
    directory, filename = os.path.split(MILVUS_DB_URI)
    return os.path.join(directory, f".{filename}.lock")


def add_document(
    *,
    doc_id: str,
    original_filename: str,
    stored_path: str,
    file_hash: str,
    chunks,
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO documents (id, original_filename, stored_path, sha256, chunk_count) VALUES (?,?,?,?,?)",
        (doc_id, original_filename, stored_path, file_hash, len(chunks)),
    )
    conn.executemany(
        "INSERT INTO chunks (doc_id, chunk_index, content, metadata_json) VALUES (?,?,?,?)",
        [
            (doc_id, i, c.page_content, json.dumps(dict(c.metadata)))
            for i, c in enumerate(chunks)
        ],
    )
    conn.commit()
    logger.info("Stored doc %s (%d chunks) in database", doc_id, len(chunks))


def get_by_hash(sha: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE sha256=?", (sha,)).fetchone()
    return dict(row) if row else None


def list_documents() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM documents ORDER BY uploaded_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_document(doc_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    return dict(row) if row else None


def delete_document(doc_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT id FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    return True


def clear_all() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM documents")
    conn.commit()
    reset_vector_store()
    for path in (MILVUS_DB_URI, _milvus_lock_path()):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                logger.warning("Could not remove %s: %s", path, e)
    if os.path.isdir(UPLOAD_DIR):
        for name in os.listdir(UPLOAD_DIR):
            path = os.path.join(UPLOAD_DIR, name)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError as e:
                    logger.warning("Could not remove upload %s: %s", path, e)


def load_chunks(doc_ids: list[str] | None = None) -> list[Document]:
    conn = get_connection()
    if doc_ids:
        placeholders = ",".join("?" * len(doc_ids))
        rows = conn.execute(
            f"SELECT content, metadata_json FROM chunks WHERE doc_id IN ({placeholders}) ORDER BY doc_id, chunk_index",
            doc_ids,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT content, metadata_json FROM chunks ORDER BY doc_id, chunk_index"
        ).fetchall()
    return [
        Document(page_content=r["content"], metadata=json.loads(r["metadata_json"]))
        for r in rows
    ]


def has_documents() -> bool:
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    return count > 0
