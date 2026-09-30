"""
Tests for API Hardening, Error Handling, and Request Tracing.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_x_request_id_header():
    res = client.get("/")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers

def test_custom_x_request_id():
    res = client.get("/", headers={"X-Request-ID": "custom-id-999"})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == "custom-id-999"

def test_structured_404_error_response():
    res = client.get("/documents/non-existent-id-999")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] in ["DOCUMENT_NOT_FOUND", "HTTP_404"]
    assert "request_id" in data["error"]


def test_hybrid_search_api():
    res = client.post("/search/hybrid", json={"query": "termination notice", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "results" in data

def test_advanced_rag_api():
    res = client.post("/rag/advanced", json={"query": "What is the termination period?", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "retrieval" in data

def test_audit_logs_api():
    res = client.get("/audit/logs")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
