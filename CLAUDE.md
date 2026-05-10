# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup
```sh
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Run
```sh
# Backend (FastAPI) — http://localhost:8000
uvicorn backend.main:app --reload --reload-dir backend

# Frontend (Streamlit) — http://localhost:8501
streamlit run frontend/app.py
```

Ollama must be running with the configured model before starting:
```sh
ollama pull llama3.2:1b  # default; override with OLLAMA_MODEL env var
```

### Tests
```sh
pytest tests/test_retrieval.py
pytest tests/test_router.py
```

### Syntax check (no linter configured)
```sh
python -m compileall backend frontend
```

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2:1b` | Ollama model name |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint |

## Architecture

The system is a local-first document QA pipeline: users upload documents via a Streamlit UI, which are embedded into a Milvus vector store, then queried via hybrid retrieval and answered by a local Ollama LLM.

### Request lifecycle

```
Streamlit (frontend/app.py)
  └─ HTTP → FastAPI (backend/main.py)
              ├─ POST /upload  → ingestion.py → parser → chunker → vectordb
              ├─ POST /query   → router.py → retrieval.py → generator.py → Ollama
              └─ POST /documents/clear → active_doc.py + vectordb cleanup
```

### Backend services (`backend/services/`)

| Module | Role |
|---|---|
| `router.py` | Classifies query intent: doc QA / general chat / live-data rejection |
| `ingestion.py` | Orchestrates parse → chunk → embed → store |
| `parser.py` | Unstructured auto-detection for PDF, DOCX, TXT, images |
| `chunker.py` | `RecursiveCharacterTextSplitter` (size=1000, overlap=200), groups by page, attaches metadata |
| `retrieval.py` | Hybrid lexical + vector search, reranking, deduplication, returns K=4 chunks |
| `generator.py` | Builds prompt, calls Ollama, keyword-extraction fallback |
| `vectordb.py` | Milvus Lite singleton with threading lock |
| `active_doc.py` | Loads/saves/clears `active_document.json` chunk cache |

### Key design decisions

- **`/query` is synchronous** (not `async def`) because Milvus and Ollama calls are blocking; avoids stalling the FastAPI event loop.
- **File deduplication via SHA256**: `/upload` skips re-ingestion if the same file hash was already processed.
- **Milvus Lite**: uses embedded `milvus_demo.db` file — no standalone Milvus server needed.
- **Domain-aware retrieval scoring**: summary queries bias early pages; professor/instructor queries bias pages 1–2; email queries bonus-score chunks containing `@`; short acronym queries double-weight exact word-boundary matches.
- **Fallback chain in generator**: if the LLM response is ambiguous and the query is a short keyword, the system extracts text snippets directly rather than returning a vague answer.

### Runtime artifacts (not committed)

| Path | Purpose |
|---|---|
| `uploads/` | Uploaded files (UUID-prefixed) |
| `milvus_demo.db` | Milvus vector DB |
| `active_document.json` | Serialized chunk cache |
| `.env` | Local env overrides |

## Code conventions

- snake_case functions/variables, PascalCase classes, UPPERCASE module-level constants.
- Imports ordered: stdlib → third-party → local.
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `refactor:`, etc.).
