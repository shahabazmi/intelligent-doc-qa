import re
from collections import defaultdict

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .parser import parse_document


def _detect_section(text: str) -> str:
    """Extract a section heading from the first few lines of a page text block."""
    for line in text.split("\n")[:6]:
        s = line.strip()
        if len(s) < 3 or len(s) > 80:
            continue
        # All-caps heading: "INTRODUCTION", "CHAPTER 1"
        if s.isupper() and len(s) >= 4:
            return s
        # Numbered section: "1.", "1.1", "Chapter 1", "Section 2", "I. ", "II."
        if re.match(r'^(\d+\.|\d+\.\d+\.?|[IVXLC]+\.\s|Chapter\s+\d+|Section\s+\d+)', s, re.IGNORECASE):
            return s[:80]
        # Short title-case line with no trailing period and no inline punctuation
        words = s.split()
        if (2 <= len(words) <= 8 and s[0].isupper()
                and not s.endswith(".") and "," not in s and ";" not in s):
            return s
    return ""


def _normalize_chunk_text(text: str) -> str:
    """Collapse whitespace for prose; preserve line breaks for tables/structured data."""
    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        return ""
    # If >40% of lines are short and contain digits — treat as table/structured data
    numeric_short = sum(1 for l in lines if len(l.strip()) < 80 and any(c.isdigit() for c in l))
    if len(lines) >= 3 and numeric_short / len(lines) > 0.4:
        return "\n".join(" ".join(l.split()) for l in lines)
    return " ".join(text.split())


def chunk_document(file_path, doc_id: str = ""):
    raw = parse_document(file_path)

    # Tables are kept atomic (never split); text is grouped per page and split.
    table_docs: list[Document] = []
    grouped_pages: dict[int, list[str]] = defaultdict(list)
    page_sources: dict[int, str] = {}
    for elem in raw:
        meta = elem.get("metadata") or {}
        page = meta.get("page_number") or 1
        source = meta.get("filename") or ""
        page_sources[page] = source
        if str(meta.get("category", "")).lower() == "table":
            table_docs.append(
                Document(
                    page_content=elem["text"],
                    metadata={
                        "source": source,
                        "page": page,
                        "doc_id": doc_id,
                        "section": "Table",
                        "category": "Table",
                    },
                )
            )
        else:
            grouped_pages[page].append(elem["text"])

    docs = []
    for page in sorted(grouped_pages):
        page_text = "\n\n".join(grouped_pages[page])
        docs.append(
            Document(
                page_content=page_text,
                metadata={
                    "source": page_sources[page],
                    "page": page,
                    "doc_id": doc_id,
                    "section": _detect_section(page_text),
                },
            )
        )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    # Append atomic table chunks so financial/structured rows stay together.
    chunks.extend(table_docs)
    for index, chunk in enumerate(chunks):
        if chunk.metadata.get("category") != "Table":
            chunk.page_content = _normalize_chunk_text(chunk.page_content)
        chunk.metadata["chunk_index"] = index
        # Ensure section key always exists (inherited from page doc; set "" if missing)
        chunk.metadata.setdefault("section", "")
    return chunks
