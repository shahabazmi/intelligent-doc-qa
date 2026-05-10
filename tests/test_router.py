from backend.services.router import is_live_data_query, looks_like_document_query


def test_document_questions_route_to_active_document():
    assert looks_like_document_query("who is the instructor", True)
    assert looks_like_document_query("summarize this pdf", True)


def test_general_chat_does_not_route_to_documents():
    assert not looks_like_document_query("hello", True)
    assert not looks_like_document_query("tell me a joke", True)
    assert not looks_like_document_query("how are you today", True)
    assert not looks_like_document_query("who is Abdul Kalam", True)
    assert not looks_like_document_query("do you know Donald Trump", True)
    assert not looks_like_document_query("how are you", True)


def test_live_data_query_is_not_treated_as_document_qa():
    assert is_live_data_query("what's the weather in moscow today")
    assert not looks_like_document_query("what's the weather in moscow today", True)


def test_no_active_document_means_no_document_routing():
    assert not looks_like_document_query("who is the instructor", False)
