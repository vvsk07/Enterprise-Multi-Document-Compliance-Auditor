"""
Tests for Workstream 2: Cross-Encoder Reranking.
"""

import pytest
from app.services.reranker_service import RerankerService

def test_reranker_status():
    service = RerankerService()
    status = service.get_status()
    assert "enabled" in status
    assert "model_name" in status
    assert "available" in status

def test_reranker_empty_candidates():
    service = RerankerService()
    results = service.rerank("termination notice", [], top_k=5)
    assert results == []

def test_reranker_ranking():
    service = RerankerService()
    candidates = [
        {"chunk_id": "c1", "text": "The quick brown fox jumps over the lazy dog.", "score": 0.5},
        {"chunk_id": "c2", "text": "Either party may terminate this agreement with 30 days notice.", "score": 0.6}
    ]
    results = service.rerank("termination notice", candidates, top_k=2)
    assert len(results) == 2
    assert "reranker_score" in results[0]
    # Candidate c2 is clearly more relevant to "termination notice"
    assert results[0]["chunk_id"] == "c2"

def test_reranker_fallback_when_disabled():
    service = RerankerService()
    service.enabled = False
    candidates = [
        {"chunk_id": "c1", "text": "Text 1", "score": 0.8},
        {"chunk_id": "c2", "text": "Text 2", "score": 0.4}
    ]
    results = service.rerank("query", candidates, top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
