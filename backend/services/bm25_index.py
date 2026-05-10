from __future__ import annotations

import re

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def score_chunks(query: str, chunks) -> list[float]:
    """Return a BM25 score for each chunk against the query."""
    corpus = [_tokenize(doc.page_content) for doc in chunks]
    if not corpus:
        return []
    return list(BM25Okapi(corpus).get_scores(_tokenize(query)))
