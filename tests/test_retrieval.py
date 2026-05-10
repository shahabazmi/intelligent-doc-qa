from langchain_core.documents import Document

from backend.services.bm25_index import score_chunks
from backend.services.retrieval import _is_summary_query, _lexical_score


def test_summary_query_detection():
    assert _is_summary_query("what is this pdf about?")
    assert _is_summary_query("summary of this document")
    assert not _is_summary_query("who is the instructor")


def test_professor_query_prefers_instructor_chunk():
    instructor_doc = Document(
        page_content="Instructor: Assoc. Prof. Soroosh Shalileh Email: sshalileh@hse.ru",
        metadata={"page": 1, "chunk_index": 0, "source": "course.pdf"},
    )
    generic_doc = Document(
        page_content="Short report (3-5 pages) explaining results.",
        metadata={"page": 7, "chunk_index": 10, "source": "course.pdf"},
    )

    instructor_score = _lexical_score("who is the professor in this pdf", instructor_doc)
    generic_score = _lexical_score("who is the professor in this pdf", generic_doc)

    assert instructor_score > generic_score


def test_bm25_ranks_relevant_chunk_higher():
    # BM25Okapi IDF is 0 when exactly half the corpus matches; need ≥4 docs
    docs = [
        Document(page_content="machine learning algorithms use gradient descent optimization", metadata={}),
        Document(page_content="the weather today is sunny and warm outside", metadata={}),
        Document(page_content="natural language processing uses deep neural networks", metadata={}),
        Document(page_content="the stock market closed higher yesterday afternoon", metadata={}),
    ]
    scores = score_chunks("machine learning", docs)
    assert scores[0] > scores[1]
