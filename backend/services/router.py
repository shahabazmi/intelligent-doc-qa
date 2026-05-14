import re

DOCUMENT_REFERENCE_PATTERNS = (
    r"\b(uploaded|attached|provided)\s+(pdf|document|file|paper|report)\b",
    r"\b(this|that|the)\s+(pdf|document|file|paper|report)\b",
    r"\bfrom\s+(the\s+)?(pdf|document|file|paper|report|upload)\b",
    r"\bin\s+(the\s+)?(pdf|document|file|paper|report|upload)\b",
    r"\baccording\s+to\s+(the\s+)?(pdf|document|file|paper|report|upload)\b",
    r"\bbased\s+on\s+(the\s+)?(pdf|document|file|paper|report|upload)\b",
)
DOCUMENT_ACTION_PREFIXES = (
    "who is the",
    "who are the",
    "what is the",
    "what is",
    "what are the",
    "what are",
    "what was the",
    "what was",
    "what were the",
    "what were",
    "what does the",
    "what does this",
    "what did the",
    "what did",
    "when is the",
    "when was the",
    "when was",
    "when are the",
    "when did the",
    "when did",
    "where is the",
    "where are the",
    "where did the",
    "where does the",
    "how many",
    "how much",
    "how does the",
    "how did",
    "how was",
    "how were",
    "why did",
    "why does",
    "why was",
    "summarize",
    "summary",
    "key points",
    "main points",
    "explain this",
    "explain the",
    "describe the",
    "list the",
    "find the",
    "extract",
    "outline",
    "show me the",
    "give me the",
    "tell me the",
)
GENERAL_CHAT_PREFIXES = (
    "hello",
    "hi",
    "hey",
    "thanks",
    "thank you",
    "write",
    "draft",
    "tell me a joke",
    "translate",
    "how are you",
    "how do you feel",
    "how's",
    "who are you",
    "what are you",
    "do you",
    "can you",
    "could you",
    "i am",
    "i'm",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
)
LIVE_DATA_PATTERNS = (
    r"\bweather\b",
    r"\bforecast\b",
    r"\btemperature\b",
    r"\blatest news\b",
    r"\bstock price\b",
    r"\bcrypto price\b",
    r"\bsports score\b",
    r"\bscore today\b",
    r"\btoday in\b",
    r"\bright now\b",
    r"\bcurrent\b.*\b(weather|price|score|news)\b",
)


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().strip(".,!?").split())


def mentions_document(query: str) -> bool:
    text = normalize_query(query)
    return any(re.search(pattern, text) for pattern in DOCUMENT_REFERENCE_PATTERNS)


def is_live_data_query(query: str) -> bool:
    text = normalize_query(query)
    return any(re.search(pattern, text) for pattern in LIVE_DATA_PATTERNS)


def looks_like_document_query(query: str, has_documents: bool) -> bool:
    text = normalize_query(query)
    if not has_documents:
        return False
    if mentions_document(query):
        return True
    if is_live_data_query(query):
        return False
    if any(text.startswith(prefix) for prefix in GENERAL_CHAT_PREFIXES):
        return False
    return any(text.startswith(prefix) for prefix in DOCUMENT_ACTION_PREFIXES)
