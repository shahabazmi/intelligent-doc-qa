from __future__ import annotations

import re

from rank_bm25 import BM25Okapi


_TOKEN_RE = re.compile(
    r"\$?\d[\d,.]*%?"          # $1,234.56  25%  2024  3.14
    r"|\b\w+(?:-\w+)*\b"        # state-of-the-art  COVID-19  M3
)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def score_chunks(query: str, chunks) -> list[float]:
    """Return a BM25 score for each chunk against the query."""
    corpus = [_tokenize(doc.page_content) for doc in chunks]
    if not corpus:
        return []
    return list(BM25Okapi(corpus).get_scores(_tokenize(query)))
