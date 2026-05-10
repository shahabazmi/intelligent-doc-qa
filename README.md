# Enterprise Doc AI

A local-first document question-answering system. Upload PDFs, Word docs, text files, or images, and ask questions in natural language — answers come from your documents (or general knowledge) without any data leaving your machine.

The stack is fully local: **Ollama** for the LLM, **Milvus Lite** for vector search, **SQLite** for documents and conversations, **FastAPI** for the API, and **Streamlit** for the UI.

---

## Features

- **Multi-format ingestion** — PDF, DOCX, TXT, PNG, JPG, JPEG via Unstructured.
- **Hybrid retrieval** — BM25 lexical search fused with dense vector similarity (BAAI/bge-small-en-v1.5).
- **Query-aware retrieval** — a classifier tags each query as extractive, numerical, provenance, list, summary, reasoning, or factual, then tunes `top_k`, BM25 weight, and answer length accordingly.
- **Conversation memory** — multi-turn chats with title auto-generation, rename, and delete.
- **Smart routing** — questions about uploaded documents go to RAG; greetings and general chat go straight to the LLM; weather queries hit a free real-time service (wttr.in).
- **Deduplication** — files are hashed (SHA-256) on upload and never re-ingested.
- **Resilient state** — if `milvus_demo.db` is missing on startup, the vector store is rebuilt automatically from the SQLite chunk cache.

---

## Architecture

```
Streamlit UI (frontend/app.py)
       │  HTTP
       ▼
FastAPI (backend/main.py)
       │
       ├── /upload          → ingestion → parser → chunker → vectordb + SQLite
       ├── /query           → router → classifier → retrieval (BM25 + vector) → generator → Ollama
       ├── /documents/*     → list / delete / clear
       └── /conversations/* → start / list / get / rename / delete
```

### Backend services (`backend/services/`)

| Module | Responsibility |
|---|---|
| `router.py` | Routes a query to document QA, general chat, or live-data |
| `query_classifier.py` | Classifies query into 7 types and produces a `QueryConfig` |
| `parser.py` | Unstructured auto-detection for supported file types |
| `chunker.py` | `RecursiveCharacterTextSplitter` (size 1000, overlap 200), page-aware metadata |
| `ingestion.py` | Orchestrates parse → chunk → embed → persist |
| `vectordb.py` | Milvus Lite singleton with thread-safe init |
| `bm25_index.py` | BM25Okapi scoring over chunks |
| `retrieval.py` | Hybrid BM25 + vector retrieval, reranking, deduplication |
| `generator.py` | Prompt construction and Ollama calls (document QA + general chat) |
| `document_store.py` | SQLite-backed document/chunk persistence |
| `conversation.py` | SQLite-backed conversation and message history |
| `database.py` | Shared SQLite connection (WAL mode) |
| `web_data.py` | Real-time weather lookup via wttr.in |

---

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) running locally
- ~2 GB disk for the embedding model on first run

Pull a model that matches `OLLAMA_MODEL` (default `llama3.2:3b`):

```sh
ollama pull llama3.2:3b
```

---

## Setup

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The first query will download the embedding model (`BAAI/bge-small-en-v1.5`) into the local Hugging Face cache.

---

## Run

Start the backend (terminal 1):

```sh
uvicorn backend.main:app --reload --reload-dir backend
# → http://localhost:8000
```

Start the frontend (terminal 2):

```sh
streamlit run frontend/app.py
# → http://localhost:8501
```

Make sure Ollama is running (`ollama serve` if not already on).

---

## Configuration

All settings live in `backend/config.py` and can be overridden by environment variables.

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model name (must appear in `ollama list`) |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint |

Other in-code constants:

| Constant | Default | Purpose |
|---|---|---|
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-small-en-v1.5` | Sentence-transformer used for embeddings |
| `RETRIEVAL_K` | `3` | Default number of chunks returned |
| `SIMILARITY_THRESHOLD` | `1.2` | Max L2 distance; anything higher is rejected as weak |

A local `.env` is auto-loaded if present. Do not commit it.

---

## API

| Method | Path | Description |
|---|---|---|
| `GET`    | `/`                                  | Health check |
| `POST`   | `/upload`                            | Multipart file upload (field `file`) |
| `POST`   | `/query`                             | Form fields `query`, optional `conversation_id` |
| `GET`    | `/documents`                         | List uploaded documents |
| `DELETE` | `/documents/{doc_id}`                | Remove one document and rebuild the vector store |
| `POST`   | `/documents/clear`                   | Clear all documents |
| `POST`   | `/conversations`                     | Start a new conversation, returns `{id}` |
| `GET`    | `/conversations`                     | List conversations |
| `GET`    | `/conversations/{id}`                | Get conversation with full message history |
| `POST`   | `/conversations/{id}/rename`         | Rename (form field `title`) |
| `DELETE` | `/conversations/{id}`                | Delete conversation |

Example:

```sh
curl -F "file=@whitepaper.pdf" http://localhost:8000/upload
curl -F "query=Summarize the introduction" http://localhost:8000/query
```

---

## Project layout

```
enterprise-doc-ai/
├── backend/
│   ├── main.py            # FastAPI routes
│   ├── config.py          # Paths, models, retrieval limits
│   └── services/          # Parsing, chunking, retrieval, generation, persistence
├── frontend/
│   └── app.py             # Streamlit chat UI
├── tests/
│   ├── test_retrieval.py
│   └── test_router.py
├── uploads/               # User files (UUID-prefixed) — gitignored
├── milvus_demo.db         # Milvus Lite vector store — gitignored
├── app.db                 # SQLite (documents, chunks, conversations) — gitignored
└── requirements.txt
```

---

## Tests

```sh
pytest tests/test_retrieval.py
pytest tests/test_router.py
```

Quick syntax check (no linter is configured):

```sh
python -m compileall backend frontend
```

---

## Notes

- `/query` is intentionally **synchronous** — Milvus and Ollama calls are blocking, and a sync handler avoids stalling the FastAPI event loop.
- Uploaded files are user-supplied input. Treat them as untrusted before adding new file-type support to the ingestion pipeline.
- Runtime artifacts (`uploads/`, `milvus_demo.db`, `app.db`, `.env`, `venv/`) are local-only and should not be committed.
