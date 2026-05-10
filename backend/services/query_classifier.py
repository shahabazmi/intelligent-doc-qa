from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    EXTRACTIVE = "extractive"   # exact paragraph / verbatim / quote
    NUMERICAL  = "numerical"    # how many / total / percentage / date
    PROVENANCE = "provenance"   # which page / which section / source
    LIST       = "list"         # names / entities / countries / enumerations
    SUMMARY    = "summary"      # summarize / overview / key points
    REASONING  = "reasoning"    # risks / impacts / analysis / strategy
    FACTUAL    = "factual"      # default general QA


@dataclass
class QueryConfig:
    query_type: QueryType
    top_k: int
    bm25_weight: float
    max_tokens: int


_EXTRACTIVE = frozenset({
    "exact paragraph", "exact text", "exact wording", "exact line",
    "show paragraph", "show exact", "quote from", "verbatim",
    "word for word", "directly from", "as stated", "as written",
    "as defined", "copy paste", "cite this", "citation",
})

_NUMERICAL = frozenset({
    "how many", "number of", "total", "count", "percentage",
    "how much", "exact value", "statistics", "how often",
    "what date", "when was", "what year", "what month",
    "what percentage", "how long", "how far", "how large",
    "revenue", "employees", "shares", "budget",
})

_PROVENANCE = frozenset({
    "which page", "what page", "which section", "what section",
    "where does", "where is this", "source of", "where in",
    "cited on", "found on", "on what page", "in which section",
})

_LIST = frozenset({
    "list all", "list the", "what are all", "name all",
    "enumerate", "give me all", "show all",
    "all countries", "all states", "all names", "all entities",
    "what are the names", "who are all", "which ones",
})

_REASONING = frozenset({
    "what are the risks", "what are the impacts", "what are the implications",
    "analyze", "analysis of", "strategy", "competition", "competitive",
    "regulations", "regulatory", "why does", "how does",
    "what caused", "what led", "what resulted", "what effect",
})

_SUMMARY = (
    "summarize", "summary of", "what is this", "what does this",
    "overview of", "overview", "main points", "key points",
    "briefly describe", "give me a summary",
)


def classify_query(query: str) -> QueryConfig:
    q = query.lower().strip()

    if any(t in q for t in _EXTRACTIVE):
        return QueryConfig(QueryType.EXTRACTIVE, top_k=7,  bm25_weight=0.5, max_tokens=250)
    if any(t in q for t in _PROVENANCE):
        return QueryConfig(QueryType.PROVENANCE, top_k=3,  bm25_weight=0.5, max_tokens=60)
    if any(t in q for t in _NUMERICAL):
        return QueryConfig(QueryType.NUMERICAL,  top_k=5,  bm25_weight=0.7, max_tokens=60)
    if any(t in q for t in _LIST):
        return QueryConfig(QueryType.LIST,        top_k=5,  bm25_weight=0.6, max_tokens=150)
    if any(t in q for t in _REASONING):
        return QueryConfig(QueryType.REASONING,   top_k=5,  bm25_weight=0.4, max_tokens=120)
    if any(t in q for t in _SUMMARY):
        return QueryConfig(QueryType.SUMMARY,     top_k=6,  bm25_weight=0.5, max_tokens=300)

    return QueryConfig(QueryType.FACTUAL, top_k=3, bm25_weight=0.5, max_tokens=120)
