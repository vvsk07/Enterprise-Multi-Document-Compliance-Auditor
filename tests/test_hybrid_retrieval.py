"""
Tests for Workstream 1: Hybrid BM25 + FAISS Retrieval.
"""

import pytest
from app.services.bm25_service import BM25Service, tokenize_text
from app.services.hybrid_search_service import HybridSearchService
from app.services.vector_store import FAISSVectorStore


def test_bm25_tokenization():
    tokens = tokenize_text("Vendor shall provide 30-day notice.")
    assert "vendor" in tokens
    assert "provide" in tokens
    assert "30" in tokens
    assert "day" in tokens
    assert "notice" in tokens

def test_bm25_indexing_and_search():
    service = BM25Service()
    service.clear_index()

    chunk_ids = ["c1", "c2", "c3"]
    texts = [
        "Either party may terminate this agreement with 30 days written notice.",
        "Data retention policy requires customer records to be stored for 7 years.",
        "Unrelated facility access procedures."
    ]
    meta = [
        {"document_id": "doc1", "document_type": "Contract"},
        {"document_id": "doc2", "document_type": "Policy"},
        {"document_id": "doc3", "document_type": "Procedure"}
    ]

    service.add_chunks(chunk_ids, texts, meta)
    assert len(service.metadata_store) == 3

    # Search terminate notice
    results = service.search("terminate notice", top_k=5)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "c1"
    assert results[0]["bm25_score"] >= 0.0

    # Search metadata filtering
    filtered = service.search("policy", top_k=5, filters={"document_type": "Policy"})
    assert len(filtered) == 1
    assert filtered[0]["chunk_id"] == "c2"


def test_hybrid_search_fusion():
    hybrid_service = HybridSearchService()
    results = hybrid_service.search("notice contract", top_k=5)
    assert isinstance(results, list)

def test_empty_query_hybrid_search():
    hybrid_service = HybridSearchService()
    results = hybrid_service.search("", top_k=5)
    assert results == []
