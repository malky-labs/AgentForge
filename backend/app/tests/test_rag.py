import pytest
from app.services.rag_engine import (
    split_text_into_chunks,
    extract_text_from_markdown,
    extract_text_from_web,
    rag_engine
)

def test_markdown_text_stripping():
    md = "# Title\nSome content with **bold** text and <div>HTML tags</div>."
    clean = extract_text_from_markdown(md)
    assert "<div" not in clean
    assert "Title" in clean

def test_web_text_html_stripping():
    html = "<html><body><h1>Headline</h1><p>Main text context.</p></body></html>"
    clean = extract_text_from_web(html)
    assert "Headline" in clean
    assert "Main text context" in clean

def test_character_overlapping_chunks():
    text = "abcdefghijklmnopqrstuvwxyz"
    # size 10, overlap 2
    chunks = split_text_into_chunks(text, chunk_size=10, chunk_overlap=2)
    
    assert len(chunks) > 0
    assert chunks[0] == "abcdefghij"
    # Overlap boundary starts at index 8 (10 - 2) which is 'i'
    assert chunks[1] == "ijklmnopqr"

@pytest.mark.asyncio
async def test_citation_context_building(monkeypatch):
    # Mock embedding function
    async def mock_get_embedding(self, text):
        return [0.1] * 384
    monkeypatch.setattr(type(rag_engine), "get_embedding", mock_get_embedding)

    # Mock query returning documents
    async def mock_query_knowledge(self, collection_id, query, limit=3):
        return [
            {
                "content": "Python is a program language.",
                "document_name": "python.txt",
                "document_id": "doc_123",
                "chunk_index": 0,
                "score": 0.2
            }
        ]
    monkeypatch.setattr(type(rag_engine), "query_knowledge", mock_query_knowledge)

    context = await rag_engine.build_citations_context("mock-col-id", "python")
    assert "[Retrieved Context from Knowledge Base Collections]" in context
    assert "python.txt" in context
    assert "Python is a program language" in context
