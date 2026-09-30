"""
Tests for Workstream 3 & 4: Advanced RAG Pipeline & Query Understanding.
"""

import pytest
from app.services.query_analysis_service import query_analysis_service
from app.services.advanced_rag_service import advanced_rag_service

def test_query_analysis_compliance():
    analysis = query_analysis_service.analyze_query("What is the vendor termination notice period?")
    assert analysis["question_type"] in ["compliance_lookup", "quantitative_lookup", "fact_lookup"]
    assert "termination" in analysis["compliance_terms"]
    assert analysis["document_scope"] in ["All", "Contract"]


def test_query_analysis_contradiction():
    analysis = query_analysis_service.analyze_query("Is there a conflict between retention periods?")
    assert analysis["question_type"] == "contradiction_check"
    assert "conflict" in analysis["contradiction_terms"]

def test_advanced_rag_query_structure():
    res = advanced_rag_service.query("What is the termination notice period?", top_k=3)
    assert "question" in res
    assert "answer" in res
    assert "confidence" in res
    assert "citations" in res
    assert "sources" in res
    assert "retrieval" in res
    assert "bm25_candidates" in res["retrieval"]
    assert "dense_candidates" in res["retrieval"]

def test_advanced_rag_insufficient_evidence():
    res = advanced_rag_service.query("XYZ123NonExistentTermQuery", minimum_score=0.99)
    assert "Insufficient evidence" in res["answer"]
    assert res["confidence"] == 0.0
