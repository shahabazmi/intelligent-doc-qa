# Repository Guidelines

## Project Structure & Module Organization

This is a Python document QA app with a FastAPI backend and Streamlit frontend.

- `backend/main.py` defines API routes for health, document upload, and query.
- `backend/config.py` centralizes paths, model names, Ollama settings, and retrieval limits.
- `backend/services/` contains parsing, chunking, ingestion, vector storage, retrieval, and answer generation.
- `frontend/app.py` is the Streamlit chat UI and calls the backend at `http://localhost:8000`.
- `uploads/`, `milvus_demo.db`, `.env`, `venv/`, and `__pycache__/` are local runtime artifacts and should not be committed.

## Build, Test, and Development Commands

Create and activate a local environment:

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the backend:

```sh
uvicorn backend.main:app --reload --reload-dir backend
```

Run the frontend in a second terminal:

```sh
streamlit run frontend/app.py
```

Before querying, ensure Ollama is running and has the configured model:

```sh
ollama pull llama3.2:1b
```

Override defaults with environment variables such as `OLLAMA_MODEL` and `OLLAMA_BASE_URL`.

## Coding Style & Naming Conventions

Use standard Python style: 4-space indentation, snake_case for functions and modules, PascalCase for classes, and uppercase names for constants. Keep service modules focused on one responsibility, matching the existing `backend/services/*.py` pattern. Prefer explicit exceptions and small helper functions over large route handlers. Keep imports grouped as standard library, third-party, then local imports.

## Testing Guidelines

No automated test suite is currently checked in. For new behavior, add `pytest` tests under `tests/` using names like `test_ingestion.py` and `test_query_api.py`. Until a test runner is added to `requirements.txt`, run a syntax smoke check:

```sh
python -m compileall backend frontend
```

For API changes, also exercise `/upload` and `/query` manually through the Streamlit UI or HTTP client.

## Commit & Pull Request Guidelines

This directory has no Git history available, so use clear Conventional Commit-style messages such as `feat: add OCR parser fallback` or `fix: handle empty retrieval results`. Pull requests should include a short summary, affected backend/frontend paths, manual test results, and screenshots for visible UI changes. Link issues when available and call out any model, database, or environment changes.

## Security & Configuration Tips

Do not commit uploaded documents, local vector databases, virtual environments, or secrets. Keep `.env` local. Treat uploaded files as untrusted input and validate new file types before adding them to the ingestion path.
