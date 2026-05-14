from __future__ import annotations

import re
from typing import Optional

from langchain_community.llms import Ollama

from ..config import LLM_MODEL_NAME, OLLAMA_BASE_URL
from .query_classifier import QueryConfig, QueryType

SYSTEM_PROMPT = """
You are a highly accurate document-grounded AI assistant.

You must answer questions ONLY from the provided document context.

RULES:
1. Use ONLY the retrieved context provided to you.
2. Do NOT use outside knowledge.
3. Do NOT make assumptions.
4. Do NOT generate information that is not present in the context.
5. If the answer is not clearly available in the context, reply:
   "I could not find this information in the document."
6. Keep answers concise, factual, and grounded.
7. Do NOT provide generic explanations.
8. Do NOT add extra details beyond the context.
9. If multiple relevant points exist, summarize them clearly.
10. Do NOT repeat previous questions or previous answers.

Your goal is to provide accurate and document-faithful answers only.
"""

GREETINGS = {
    "hi", "hello", "hey", "hi!", "hello!", "hey!",
    "good morning", "good afternoon", "good evening",
    "how are you", "how are you?", "how are you today", "how are you today?",
    "how's it going", "how are things", "what's up", "whats up",
}

# Queries that want raw chunk text returned verbatim — LLM is skipped entirely
_EXTRACTIVE_TRIGGERS = frozenset({
    "exact paragraph", "exact text", "exact wording", "exact line",
    "show paragraph", "show exact", "quote from", "verbatim",
    "word for word", "directly from", "as stated", "as written",
    "as defined", "copy paste", "cite this", "citation",
})

# Type-specific addenda appended to the base prompt
_TYPE_ADDENDUM: dict[QueryType, str] = {
    QueryType.NUMERICAL: """
NUMERICAL RULES (ENFORCE NOW):
- Extract exact numbers, dates, percentages exactly as written in the text.
- No rounding, no estimation, no approximation.
- Return ONLY the exact value from the document.""",

    QueryType.LIST: """
LIST RULES (ENFORCE NOW):
- Return ONLY items explicitly listed in the retrieved text.
- Do NOT add items absent from the context.
- Do NOT auto-complete, expand, or infer the list.
- Do NOT add disclaimers, notes, or conversational filler.""",

    QueryType.REASONING: """
REASONING RULES (ENFORCE NOW):
- Summarize ONLY evidence explicitly stated in the retrieved text.
- FORBIDDEN phrases: "could lead to", "may result in", "potentially", "likely to",
  "creates advantages", "helps reduce", "analysts believe", "market trends suggest".
- Do NOT generate market analysis, strategic interpretation, or economic implications.
- If the document contains no relevant analysis, reply: Not found in document.""",

    QueryType.SUMMARY: """
SUMMARY RULES (ENFORCE NOW):
- Include ONLY information directly related to the question topic.
- Do NOT broaden scope to unrelated business, financial, or technical topics.
- Keep the summary tightly scoped to retrieved evidence only.""",
}



_STOP_TOKENS = [
    "\n\nQuestion:",
    "\n\nContext:",
    "\nQuestion:",
    "\nContext:",
    "Explanation:",
    "Note:",
    "Disclaimer:",
    "In conclusion",
    "P.S.",
]

_GENERIC_OPENERS_RE = re.compile(
    r"^\s*(?:"
    r"based on (?:the )?(?:provided |retrieved )?(?:document|context|information|text)[,:\s\-—]+|"
    r"according to (?:the )?(?:provided |retrieved )?(?:document|context|text|information)[,:\s\-—]+|"
    r"the (?:document|context) (?:states|says|mentions|indicates|notes|provides|shows)[,:\s\-—]+|"
    r"in (?:the )?(?:provided |retrieved )?(?:document|context|text)[,:\s\-—]+|"
    r"from (?:the )?(?:provided |retrieved )?(?:document|context|text)[,:\s\-—]+|"
    r"(?:answer|response)[,:\s\-—]+"
    r")",
    re.IGNORECASE,
)


def _clean_answer(text: str) -> str:
    """Strip generic explanatory openers ('Based on the document, …') and trim."""
    text = (text or "").strip()
    # Strip nested openers if the model stacked them ("Based on the document, according to…")
    prev = None
    while text and text != prev:
        prev = text
        text = _GENERIC_OPENERS_RE.sub("", text).lstrip(" ,:.-—")
    return text


def _build_llm(max_tokens: int = 150) -> Ollama:
    return Ollama(
        model=LLM_MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        timeout=600,
        num_predict=max_tokens,
        stop=_STOP_TOKENS,
    )


def _build_history_block(history: list[dict], max_turns: int = 3) -> str:
    """Short, clearly-labeled history block — prevents style/topic contamination."""
    if not history:
        return ""
    recent = history[-(max_turns * 2):]
    lines = []
    for turn in recent:
        role = "User" if turn["role"] == "user" else "AI"
        text = " ".join(turn["content"].split())[:80]
        if len(turn["content"]) > 80:
            text += "…"
        lines.append(f"  [{role}] {text}")
    return "[Prior conversation — for context only, do NOT copy its phrasing]\n" + "\n".join(lines) + "\n"


def _is_extractive(query: str) -> bool:
    q = query.lower()
    return any(t in q for t in _EXTRACTIVE_TRIGGERS)


def _extract_direct(docs) -> str:
    """Return top chunk text verbatim with source citation — no LLM involved."""
    if not docs:
        return "No exact paragraph found in retrieved context."
    top = docs[0]
    source  = top.metadata.get("source", "?")
    page    = top.metadata.get("page", "?")
    section = top.metadata.get("section", "")
    citation = f"(Source: {source}, Page {page}"
    if section:
        citation += f", Section: {section}"
    citation += ")"
    return f"{top.page_content}\n\n{citation}"


def _provenance_answer(docs) -> str:
    """Answer source/page/section questions from chunk metadata only — no LLM."""
    if not docs:
        return "Not found in document."
    seen, parts = set(), []
    for d in docs[:4]:
        source  = d.metadata.get("source", "?")
        page    = d.metadata.get("page", "?")
        section = d.metadata.get("section", "")
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        entry = f"Source: {source}, Page {page}"
        if section:
            entry += f", Section: {section}"
        parts.append(entry)
    return "\n".join(parts) if parts else "Not found in document."


def _build_context(docs, max_chars: int = 3000) -> str:
    """Build context string, capping total characters so 3b model isn't overwhelmed."""
    parts, total = [], 0
    for d in docs:
        source  = d.metadata.get("source", "?")
        page    = d.metadata.get("page", "?")
        section = d.metadata.get("section", "")
        header  = f"[Source: {source}, Page {page}"
        if section:
            header += f", Section: {section}"
        header += "]"
        block = f"{header}\n{d.page_content}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n\n---\n\n".join(parts)


def generate_answer(
    query: str,
    docs,
    history: Optional[list[dict]] = None,
    config: Optional[QueryConfig] = None,
) -> str:
    """Answer strictly from the retrieved document chunks."""
    if config is None:
        config = QueryConfig(QueryType.FACTUAL, top_k=3, bm25_weight=0.5, max_tokens=120)

    # Extractive: bypass LLM — return raw chunk text directly
    if config.query_type == QueryType.EXTRACTIVE or _is_extractive(query):
        return _extract_direct(docs)

    # Provenance: answer from metadata only, no LLM
    if config.query_type == QueryType.PROVENANCE:
        return _provenance_answer(docs)

    context       = _build_context(docs)
    type_addendum = _TYPE_ADDENDUM.get(config.query_type, "")

    prompt = f"""{SYSTEM_PROMPT}
{type_addendum}
Context:
{context}

Question: {query}

Answer:"""

    out = _build_llm(config.max_tokens).invoke(prompt)
    return _clean_answer(out if isinstance(out, str) else str(out))


def generate_chat_answer(
    query: str,
    history: Optional[list[dict]] = None,
    realtime_data: Optional[str] = None,
) -> str:
    """Answer a general question, optionally with injected real-time data."""
    is_greeting = query.strip().lower().rstrip("!?.") in GREETINGS

    history_block  = "" if is_greeting else _build_history_block(history)
    realtime_block = ""
    if realtime_data:
        realtime_block = f"[Live real-time data — use this for accuracy]\n{realtime_data}\n"

    prompt = f"""You are Enterprise Doc AI, a knowledgeable and helpful AI assistant.

CURRENT QUESTION: {query}

{realtime_block}{history_block}INSTRUCTIONS:
- Answer ONLY the current question above — nothing else.
- NEVER open with "I'm doing well" or any filler phrase unless the user is greeting you.
- NEVER carry over topics from previous conversation into this answer.
- If real-time data is provided, use it to give accurate, current information.
- For factual questions (people, places, history, science): give detailed, accurate answers.
- For greetings or "how are you": respond warmly and naturally — that's all.
- Be direct, informative, and comprehensive.

ANSWER:"""

    out = _build_llm(max_tokens=400).invoke(prompt)
    return (out if isinstance(out, str) else str(out)).strip()
