from __future__ import annotations

import logging
import re

from ..config import RETRIEVAL_K, SIMILARITY_THRESHOLD
from .bm25_index import score_chunks
from .document_store import load_chunks
from .vectordb import init_vector_store, reset_vector_store

logger = logging.getLogger(__name__)

_CROSS_ENCODER = None
_CROSS_ENCODER_FAILED = False
_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _cross_encoder():
    """Lazy-load cross-encoder for neural rerank. Falls back to None on failure."""
    global _CROSS_ENCODER, _CROSS_ENCODER_FAILED
    if _CROSS_ENCODER_FAILED:
        return None
    if _CROSS_ENCODER is None:
        try:
            from sentence_transformers import CrossEncoder
            _CROSS_ENCODER = CrossEncoder(_CROSS_ENCODER_MODEL)
        except Exception as e:
            logger.warning("Cross-encoder unavailable, hybrid-only rerank: %s", e)
            _CROSS_ENCODER_FAILED = True
            return None
    return _CROSS_ENCODER


def _neural_rerank(query: str, candidates: list, k: int):
    """Cross-encoder pass — picks the precise chunk over merely-related ones."""
    if not candidates:
        return candidates
    ce = _cross_encoder()
    if ce is None:
        return candidates[:k]
    try:
        pairs = [(query, (doc.page_content or "")[:512]) for doc in candidates]
        scores = ce.predict(pairs, show_progress_bar=False)
    except Exception as e:
        logger.warning("Cross-encoder predict failed: %s", e)
        return candidates[:k]
    ordered = [doc for _, doc in sorted(
        zip(scores, candidates),
        key=lambda pair: -float(pair[0]),
    )]
    return _dedupe_documents(ordered)[:k]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "pdf",
    "document",
    "file",
    "paper",
    "report",
    "said",
    "say",
    "says",
    "show",
    "tell",
    "the",
    "this",
    "to",
    "about",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}
TERM_ALIASES = {
    "professor": {"professor", "prof", "instructor", "lecturer", "teacher"},
    "prof": {"professor", "prof", "instructor", "lecturer", "teacher"},
    "instructor": {"professor", "prof", "instructor", "lecturer", "teacher"},
    "email": {"email", "mail", "contact"},
    "course": {"course", "class", "syllabus", "subject"},
}
SUMMARY_PATTERNS = (
    "summarize this pdf",
    "summarize this document",
    "summary of this pdf",
    "summary of this document",
    "what is this pdf about",
    "what is this document about",
    "what does this pdf say",
    "what does this document say",
    "overview of this pdf",
    "overview of this document",
)


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.casefold())


def _short_keyword(query: str) -> str:
    term = query.strip().strip("\"'`.,:;!?()[]{}")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,31}", term):
        return term
    return ""


NUMERICAL_TRIGGERS = frozenset({
    "how many", "number of", "total", "count", "percentage",
    "how much", "exact value", "statistics", "how often",
    "what date", "when was", "what year", "what month",
    "what percentage", "how long", "how far", "how large",
})


def _is_summary_query(query: str) -> bool:
    text = _normalize_text(query)
    return any(pattern in text for pattern in SUMMARY_PATTERNS)


def _is_numerical_query(query: str) -> bool:
    q = query.lower()
    return any(t in q for t in NUMERICAL_TRIGGERS)


def _extract_query_terms(query: str):
    terms = []
    for token in _tokenize(query):
        if token in STOPWORDS:
            continue
        if len(token) == 1:
            continue
        terms.append(token)

    expanded = set(terms)
    for term in terms:
        expanded.update(TERM_ALIASES.get(term, {term}))
    return expanded


def _document_key(doc) -> tuple[str, int, int, str]:
    return (
        str(doc.metadata.get("source", "")),
        int(doc.metadata.get("page", 0) or 0),
        int(doc.metadata.get("chunk_index", 0) or 0),
        doc.page_content,
    )


def _dedupe_documents(docs):
    unique = []
    seen = set()
    for doc in docs:
        key = _document_key(doc)
        if key in seen:
            continue
        seen.add(key)
        unique.append(doc)
    return unique


def _bigram_phrases(query: str):
    tokens = [
        token
        for token in _tokenize(query)
        if token not in STOPWORDS and len(token) > 2
    ]
    return [
        " ".join(tokens[index : index + 2])
        for index in range(len(tokens) - 1)
    ]


def _lexical_score(query: str, doc) -> int:
    """Used by _overview_chunks for summary-path ranking."""
    query_terms = _extract_query_terms(query)
    text = _normalize_text(doc.page_content)
    text_tokens = set(_tokenize(text))
    overlap = query_terms & text_tokens

    score = len(overlap) * 8
    for phrase in _bigram_phrases(query):
        if phrase in text:
            score += 8

    if any(term in query_terms for term in {"professor", "prof", "instructor"}):
        if "instructor" in text or "prof." in text or "assoc. prof." in text:
            score += 10
        if int(doc.metadata.get("page", 0) or 0) == 1:
            score += 6

    if any(term in query_terms for term in {"email", "contact"}):
        if "@" in text or "email" in text:
            score += 8

    if _is_summary_query(query):
        page = int(doc.metadata.get("page", 0) or 0)
        if page <= 2:
            score += 8
        if any(
            label in text
            for label in (
                "course description",
                "course outcomes",
                "weekly schedule",
                "main textbook",
            )
        ):
            score += 10

    if _short_keyword(query):
        pattern = re.compile(rf"\b{re.escape(_short_keyword(query))}\b", re.IGNORECASE)
        if pattern.search(doc.page_content):
            score += 10
        if re.search(rf"\({re.escape(_short_keyword(query))}\)", doc.page_content, re.IGNORECASE):
            score += 12

    if len(text) < 40:
        score -= 2

    return score


def _domain_bonus(query: str, doc) -> float:
    """Domain-specific score bonuses layered on top of the BM25+vector base."""
    query_terms = _extract_query_terms(query)
    text = _normalize_text(doc.page_content)
    bonus = 0.0

    if any(term in query_terms for term in {"professor", "prof", "instructor"}):
        if "instructor" in text or "prof." in text or "assoc. prof." in text:
            bonus += 0.15
        if int(doc.metadata.get("page", 0) or 0) == 1:
            bonus += 0.10

    if any(term in query_terms for term in {"email", "contact"}):
        if "@" in text or "email" in text:
            bonus += 0.12

    if _is_summary_query(query):
        page = int(doc.metadata.get("page", 0) or 0)
        if page <= 2:
            bonus += 0.12
        if any(
            label in text
            for label in (
                "course description",
                "course outcomes",
                "weekly schedule",
                "main textbook",
            )
        ):
            bonus += 0.15

    kw = _short_keyword(query)
    if kw:
        pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
        if pattern.search(doc.page_content):
            bonus += 0.15
        if re.search(rf"\({re.escape(kw)}\)", doc.page_content, re.IGNORECASE):
            bonus += 0.18

    if len(text) < 40:
        bonus -= 0.05

    return bonus


def _overview_chunks(chunks, k: int):
    early_chunks = [
        doc for doc in chunks if int(doc.metadata.get("page", 0) or 0) <= 2
    ] or chunks
    scored = sorted(
        early_chunks,
        key=lambda doc: (
            -_lexical_score("summary of this document", doc),
            int(doc.metadata.get("page", 0) or 0),
            int(doc.metadata.get("chunk_index", 0) or 0),
        ),
    )
    return _dedupe_documents(scored)[:k]


def _vector_candidates(query: str, count: int, doc_ids: list[str] | None = None):
    fetch_k = count if not doc_ids else count * 4
    store = init_vector_store()
    try:
        hits = store.similarity_search_with_score(query, k=fetch_k)
    except Exception as e:
        if "should create connection first" not in str(e).lower():
            raise
        reset_vector_store()
        store = init_vector_store()
        hits = store.similarity_search_with_score(query, k=fetch_k)
    docs = [doc for doc, score in hits if score <= SIMILARITY_THRESHOLD]
    if doc_ids:
        doc_id_set = set(doc_ids)
        docs = [d for d in docs if d.metadata.get("doc_id") in doc_id_set]
    return docs


def _rerank(query: str, candidates, k: int, bm25_map: dict, bm25_weight: float = 0.5):
    """Hybrid rerank: bm25_weight * norm_bm25 + (1-bm25_weight) * norm_vector_rank + domain_bonus."""
    bm25_vals = [bm25_map.get(_document_key(doc), 0.0) for doc in candidates]
    bm25_min = min(bm25_vals, default=0.0)
    bm25_max = max(bm25_vals, default=1.0)
    bm25_range = bm25_max - bm25_min or 1.0

    n = max(len(candidates), 1)
    vector_rank = {_document_key(doc): i for i, doc in enumerate(candidates)}

    def _score(doc) -> float:
        key = _document_key(doc)
        norm_bm25 = (bm25_map.get(key, 0.0) - bm25_min) / bm25_range
        norm_vec = 1.0 - vector_rank.get(key, n) / n
        return bm25_weight * norm_bm25 + (1.0 - bm25_weight) * norm_vec + _domain_bonus(query, doc)

    ranked = sorted(
        candidates,
        key=lambda doc: (
            -_score(doc),
            int(doc.metadata.get("page", 0) or 0),
            int(doc.metadata.get("chunk_index", 0) or 0),
        ),
    )
    return _dedupe_documents(ranked)[:k]


def retrieve_context(query, k=None, doc_ids: list[str] | None = None, config=None):
    if config is not None:
        k = config.top_k
        bm25_weight = config.bm25_weight
    else:
        k = k if k is not None else RETRIEVAL_K
        # Fallback: infer weighting from query keywords when no config provided.
        # Short keywords and numerical asks benefit from heavier lexical weight.
        if _is_numerical_query(query) or _short_keyword(query):
            bm25_weight = 0.75
        else:
            bm25_weight = 0.5

    chunks = load_chunks(doc_ids)
    if not chunks:
        return []

    if _is_summary_query(query):
        return _overview_chunks(chunks, max(k, 6))

    bm25_scores = score_chunks(query, chunks)
    bm25_map = {_document_key(chunks[i]): bm25_scores[i] for i in range(len(chunks))}

    # Broader candidate pools so the truly best chunk has a chance to surface.
    indexed = sorted(range(len(chunks)), key=lambda i: -bm25_scores[i])
    lexical_candidates = [chunks[i] for i in indexed[: max(k * 6, 24)]]
    vector_candidates  = _vector_candidates(query, min(len(chunks), max(k * 6, 28)), doc_ids)

    # Hybrid rerank narrows the candidate pool; neural reranker selects the precise chunk.
    hybrid_top = _rerank(
        query,
        lexical_candidates + vector_candidates,
        max(k * 4, 12),
        bm25_map,
        bm25_weight,
    )
    return _neural_rerank(query, hybrid_top, k)
