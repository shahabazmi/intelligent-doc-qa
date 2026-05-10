from __future__ import annotations

import hashlib
import logging
import os
import uuid
from threading import Lock
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import UPLOAD_DIR, MILVUS_DB_URI
from .services import document_store, conversation
from .services.ingestion import ingest_document
from .services.retrieval import retrieve_context
from .services.generator import generate_answer, generate_chat_answer
from .services.router import looks_like_document_query, is_live_data_query
from .services.web_data import get_realtime_context
from .services.query_classifier import classify_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise Doc AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}
_upload_lock = Lock()


@app.on_event("startup")
async def _rebuild_vectors_if_missing():
    """Re-embed all SQLite chunks into Milvus when the vector DB file is absent."""
    if not document_store.has_documents():
        return
    if os.path.exists(MILVUS_DB_URI):
        return
    logger.info("Vector store missing — rebuilding from SQLite chunks…")
    from .services.vectordb import init_vector_store
    from .services.document_store import load_chunks
    chunks = load_chunks()
    if not chunks:
        return
    try:
        init_vector_store().add_documents(chunks)
        logger.info("Rebuilt vector store with %d chunks", len(chunks))
    except Exception as e:
        logger.error("Vector store rebuild failed: %s", e)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _answer_from_documents(query: str, history: Optional[list[dict]] = None):
    if not document_store.has_documents():
        return {"answer": "No documents are uploaded yet. Please upload a document first.", "sources": []}

    config = classify_query(query)
    docs = retrieve_context(query, config=config)
    if not docs:
        return {"answer": "I could not find relevant information in the uploaded documents.", "sources": []}

    try:
        answer = generate_answer(query, docs, history=None, config=config)
    except (ValueError, RuntimeError, ConnectionError, TimeoutError) as e:
        raise HTTPException(503, f"LLM error — is Ollama running? {e}") from e

    sources = [
        {"file": d.metadata.get("source", "?"), "page": d.metadata.get("page", "?"), "text": d.page_content[:300]}
        for d in docs[:3]
    ]
    return {"answer": answer or "", "sources": sources}


def _answer_general(query: str, history: Optional[list[dict]] = None):
    realtime_data = None
    if is_live_data_query(query):
        try:
            realtime_data = get_realtime_context(query)
        except Exception:
            pass
    try:
        answer = generate_chat_answer(query, history=history, realtime_data=realtime_data)
    except (ValueError, RuntimeError, ConnectionError, TimeoutError) as e:
        raise HTTPException(503, f"LLM error — is Ollama running? {e}") from e
    return {"answer": answer or "", "sources": []}


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "app": "Enterprise Doc AI"}


# Documents
@app.get("/documents")
def list_documents():
    return document_store.list_documents()


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    from .services.chunker import chunk_document
    from .services.vectordb import init_vector_store, reset_vector_store

    with _upload_lock:
        doc = document_store.get_document(doc_id)
        if not doc:
            raise HTTPException(404, "Document not found")

        document_store.delete_document(doc_id)

        if os.path.exists(doc["stored_path"]):
            try:
                os.remove(doc["stored_path"])
            except OSError as e:
                logger.warning("Could not remove file %s: %s", doc["stored_path"], e)

        # Rebuild vector store from remaining documents
        remaining = document_store.list_documents()
        reset_vector_store()
        if remaining:
            store = init_vector_store()
            for rem in remaining:
                try:
                    chunks = chunk_document(rem["stored_path"], rem["id"])
                    if chunks:
                        store.add_documents(chunks)
                except (ValueError, RuntimeError) as e:
                    logger.error("Rebuild error for doc %s: %s", rem["id"], e)

    logger.info("Deleted document %s", doc_id)
    return {"status": "ok"}


@app.post("/documents/clear")
def clear_documents():
    document_store.clear_all()
    logger.info("All documents cleared")
    return {"status": "ok"}


# Conversations
@app.post("/conversations")
def start_conversation():
    cid = conversation.start_conversation()
    return {"id": cid}


@app.get("/conversations")
def list_conversations():
    return conversation.list_conversations()


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    conv = conversation.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@app.post("/conversations/{conversation_id}/rename")
def rename_conversation(conversation_id: str, title: str = Form(...)):
    if not conversation.get_conversation(conversation_id):
        raise HTTPException(404, "Conversation not found")
    conversation.rename_conversation(conversation_id, title)
    return {"status": "ok"}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    conversation.delete_conversation(conversation_id)
    return {"status": "ok"}


# Upload
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    with _upload_lock:
        existing = document_store.get_by_hash(file_hash)
        if existing:
            return {"status": "ok", "doc_id": existing["id"], "chunks": existing["chunk_count"], "file": existing["original_filename"], "reused": True}

        doc_id = uuid.uuid4().hex
        path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")
        with open(path, "wb") as f_out:
            f_out.write(content)
        try:
            n = ingest_document(path, doc_id=doc_id, original_filename=file.filename, file_hash=file_hash)
            logger.info("Uploaded %s → doc_id=%s (%d chunks)", file.filename, doc_id, n)
            return {"status": "ok", "doc_id": doc_id, "chunks": n, "file": file.filename}
        except (ValueError, RuntimeError) as e:
            if os.path.exists(path):
                os.remove(path)
            raise HTTPException(500, str(e))


# Query
@app.post("/query")
def query(query: str = Form(...), conversation_id: str = Form("")):
    """Main query endpoint — auto-routes between document QA and general chat."""
    if not query.strip():
        raise HTTPException(400, "Empty query")

    history = None
    if conversation_id:
        conv = conversation.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
        history = conversation.recent_turns(conversation_id, n=3)
        # Auto-title on first message
        if not history and not conv.get("title"):
            title = query[:60] + ("…" if len(query) > 60 else "")
            conversation.rename_conversation(conversation_id, title)

    logger.info("Query [conv=%s]: %s", conversation_id or "none", query[:80])

    if looks_like_document_query(query, document_store.has_documents()):
        result = _answer_from_documents(query, history=history)
    else:
        result = _answer_general(query, history=history)

    if conversation_id:
        conversation.append(conversation_id, "user", query)
        conversation.append(conversation_id, "assistant", result["answer"], result.get("sources", []))

    return result
