import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
MILVUS_DB_URI = os.path.join(BASE_DIR, "..", "milvus_demo.db")
APP_DB_PATH = os.path.join(BASE_DIR, "..", "app.db")
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
# Must match a name from `ollama list` (e.g. llama3.2:3b, llama3.1:8b, mistral)
LLM_MODEL_NAME = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
RETRIEVAL_K = 3
SIMILARITY_THRESHOLD = 1.2  # L2 distance — above this = weak retrieval, reject chunk
