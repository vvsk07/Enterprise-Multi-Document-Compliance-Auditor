"""
Phase 9 Scalability & Index Synthetic Benchmark Tests.
"""

import time
import pytest
from app.services.bm25_service import BM25Service

def test_synthetic_bm25_scalability():
    """Verify BM25 index handles 500 synthetic chunks without failure."""
    bm25 = BM25Service()
    syn_chunks = [{"chunk_id": f"s_{i}", "document_id": "doc_1", "text": f"Synthetic clause paragraph {i} with compliance requirements."} for i in range(500)]
    
    c_ids = [c["chunk_id"] for c in syn_chunks]
    texts = [c["text"] for c in syn_chunks]
    
    t0 = time.perf_counter()
    bm25.add_chunks(c_ids, texts, syn_chunks)
    build_time = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    res = bm25.search("compliance requirements", top_k=5)
    search_time = time.perf_counter() - t0
    
    assert build_time < 5.0, "BM25 500-chunk index build took too long"
    assert search_time < 0.1, "BM25 search latency exceeded 100ms threshold"
    assert len(res) > 0
