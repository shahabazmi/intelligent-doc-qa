from __future__ import annotations

import logging
from threading import Lock

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from pymilvus import MilvusClient, connections

from ..config import EMBEDDING_MODEL_NAME, MILVUS_DB_URI

_store: Milvus | None = None
_embeddings: HuggingFaceEmbeddings | None = None
_store_lock = Lock()
_bridge_installed = False
logger = logging.getLogger(__name__)


def _install_orm_alias_bridge() -> None:
    """Expose MilvusClient connection-manager aliases to ORM Collection calls."""
    global _bridge_installed
    if _bridge_installed or getattr(MilvusClient, "_enterprise_doc_ai_bridge", False):
        _bridge_installed = True
        return

    original_init = MilvusClient.__init__

    def bridged_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        alias = getattr(self, "_using", None)
        handler = getattr(self, "_handler", None)
        config = getattr(self, "_config", None)
        if alias and handler is not None:
            connections._alias_handlers[alias] = handler
            connections._alias_config[alias] = {
                "address": getattr(config, "address", ""),
                "user": "",
                "db_name": getattr(config, "db_name", "") or "default",
            }

    MilvusClient.__init__ = bridged_init
    MilvusClient._enterprise_doc_ai_bridge = True
    _bridge_installed = True


def init_vector_store() -> Milvus:
    """Shared Milvus store with reconnect handling for dropped aliases."""
    global _store, _embeddings
    _install_orm_alias_bridge()
    with _store_lock:
        if _store is None:
            if _embeddings is None:
                _embeddings = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL_NAME,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
            _store = Milvus(
                embedding_function=_embeddings,
                connection_args={"uri": MILVUS_DB_URI},
                collection_name="enterprise_docs",
                drop_old=False,
            )
        return _store


def reset_vector_store() -> None:
    """Drop cached client so next call rebuilds connection + store instance."""
    global _store
    with _store_lock:
        if _store is not None:
            try:
                _store.client.close()
            except Exception as e:
                logger.warning("Failed to close Milvus client: %s", e)
        _store = None
