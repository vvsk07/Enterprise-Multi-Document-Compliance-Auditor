"""
Phase 9 Evaluation Pipeline & Metric Calculation Unit Tests.
"""

import math
import pytest
from app.services.hybrid_search_service import hybrid_search_service
from app.services.bm25_service import bm25_service

def test_benchmark_dataset_structure():
    """Verify phase9_benchmark.json is valid and contains >100 queries."""
    import json
    from pathlib import Path
    bench_path = Path(__file__).resolve().parent.parent / "data" / "evaluation" / "phase9_benchmark.json"
    assert bench_path.exists(), "phase9_benchmark.json missing"
    with open(bench_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 100, f"Expected >=100 benchmark queries, got {len(data)}"
    
    q0 = data[0]
    assert "query_id" in q0
    assert "query" in q0
    assert "category" in q0
    assert "difficulty" in q0

def test_retrieval_mrr_calculation():
    """Verify MRR calculation logic."""
    relevant = ["c1"]
    retrieved_1 = ["c1", "c2", "c3"]
    retrieved_2 = ["c2", "c1", "c3"]
    retrieved_3 = ["c4", "c5"]

    def compute_rr(retrieved, rel):
        for rank, item in enumerate(retrieved, start=1):
            if item in rel:
                return 1.0 / rank
        return 0.0

    assert compute_rr(retrieved_1, relevant) == 1.0
    assert compute_rr(retrieved_2, relevant) == 0.5
    assert compute_rr(retrieved_3, relevant) == 0.0

def test_ndcg_calculation():
    """Verify nDCG@5 math formula."""
    relevant = ["c1"]
    retrieved = ["c2", "c1", "c3"]
    
    dcg5 = 0.0
    idcg5 = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), 5)))
    for rank, item in enumerate(retrieved[:5], start=1):
        if item in relevant:
            dcg5 += 1.0 / math.log2(rank + 1)
    ndcg5 = dcg5 / idcg5 if idcg5 > 0 else 0.0
    assert 0.0 < ndcg5 < 1.0
