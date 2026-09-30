"""
Phase 9 Failure Injection & Resilience Unit Tests.
"""

import pytest
from fastapi import HTTPException, Request
from app.services.search_service import search_service
from app.services.bm25_service import bm25_service
from app.services.hybrid_search_service import hybrid_search_service
from app.services.reranker_service import reranker_service
from app.core.security import RateLimiter, sanitize_filename, verify_api_key

def test_empty_query_resilience():
    """Verify empty query handling across search services."""
    assert search_service.search("") == []
    assert bm25_service.search("") == []
    assert hybrid_search_service.search("") == []
    assert reranker_service.rerank("", []) == []

def test_invalid_api_key_rejection(monkeypatch):
    """Verify missing and invalid API key rejection."""
    monkeypatch.setenv("AUDITOR_API_KEY", "test-secret-key-999")
    monkeypatch.setattr("app.core.security.get_security_config", lambda: {"enabled": True})

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(Request(scope={"type": "http"}), api_key_header=None)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(Request(scope={"type": "http"}), api_key_header="invalid-secret-key-123")
    assert exc_info.value.status_code == 401

def test_path_traversal_malicious_filenames():
    """Verify path traversal vectors are stripped safely."""
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("safe_document.pdf") == "safe_document.pdf"
