import logging

from .chunker import chunk_document
from .document_store import add_document
from .vectordb import init_vector_store, reset_vector_store

logger = logging.getLogger(__name__)


def ingest_document(file_path, *, doc_id: str, original_filename: str, file_hash: str):
    chunks = chunk_document(file_path, doc_id)
    if not chunks:
        raise ValueError("No text found")
    add_document(
        doc_id=doc_id,
        original_filename=original_filename,
        stored_path=file_path,
        file_hash=file_hash,
        chunks=chunks,
    )
    try:
        init_vector_store().add_documents(chunks)
    except Exception as e:
        if "should create connection first" not in str(e).lower():
            raise
        reset_vector_store()
        init_vector_store().add_documents(chunks)
    logger.info("Ingested %d chunks for doc_id=%s (%s)", len(chunks), doc_id, original_filename)
    return len(chunks)
