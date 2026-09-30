"""
Retrieval Benchmark Evaluation Script.
Evaluates and compares FAISS-only, BM25-only, Hybrid Search, and Hybrid + Reranker pipeline performance
across Recall@1, Recall@3, Recall@5, MRR, nDCG@5, Precision@5, Avg, P50, and P95 Latencies.
"""

import sys
import time
import json
import math
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal
from app.services.indexing_service import indexing_service
from app.services.vector_store import vector_store
from app.services.bm25_service import bm25_service
from app.services.embedding_service import embedding_service
from app.services.hybrid_search_service import hybrid_search_service
from app.services.reranker_service import reranker_service

BENCHMARK_PATH = BASE_DIR / "data" / "evaluation" / "retrieval_benchmark.json"

def calculate_relevance(item: Dict[str, Any], query_spec: Dict[str, Any]) -> bool:
    """Evaluates if a retrieved chunk matches expected query keywords/types."""
    text = item.get("text", "").lower()
    doc_type = item.get("document_type", "")

    keywords = query_spec.get("expected_keywords", [])
    expected_types = query_spec.get("expected_doc_types", [])

    keyword_match = any(kw in text for kw in keywords) if keywords else True
    type_match = doc_type in expected_types if expected_types else True
    return keyword_match and type_match

def compute_dcg(rel_flags: List[bool], k: int = 5) -> float:
    dcg = 0.0
    for idx, flag in enumerate(rel_flags[:k], 1):
        if flag:
            dcg += 1.0 / math.log2(idx + 1)
    return dcg

def run_benchmark():
    if not BENCHMARK_PATH.exists():
        print(f"Benchmark file '{BENCHMARK_PATH}' not found.")
        sys.exit(1)

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmark_queries = json.load(f)

    print(f"Loaded {len(benchmark_queries)} queries from retrieval benchmark.")

    # Ensure DB and vector index are populated
    db = SessionLocal()
    indexing_service.rebuild_index(db)
    db.close()

    systems = ["FAISS Only", "BM25 Only", "Hybrid", "Hybrid + Reranker"]
    metrics = {
        sys_name: {"r1": 0, "r3": 0, "r5": 0, "mrr": 0.0, "p5": 0.0, "ndcg5": 0.0, "latencies": []}
        for sys_name in systems
    }

    for q_item in benchmark_queries:
        query = q_item["query"]

        # 1. FAISS Only
        t0 = time.time()
        q_vec = embedding_service.embed_single(query)
        faiss_results = vector_store.similarity_search(q_vec, top_k=5)
        lat_faiss = (time.time() - t0) * 1000.0

        # 2. BM25 Only
        t0 = time.time()
        bm25_results = bm25_service.search(query, top_k=5)
        lat_bm25 = (time.time() - t0) * 1000.0

        # 3. Hybrid
        t0 = time.time()
        hybrid_results = hybrid_search_service.search(query, top_k=5)
        lat_hybrid = (time.time() - t0) * 1000.0

        # 4. Hybrid + Reranker
        t0 = time.time()
        hybrid_candidates = hybrid_search_service.search(query, top_k=20)
        reranked_results = reranker_service.rerank(query, hybrid_candidates, top_k=5)
        lat_reranker = (time.time() - t0) * 1000.0

        runs = [
            ("FAISS Only", faiss_results, lat_faiss),
            ("BM25 Only", bm25_results, lat_bm25),
            ("Hybrid", hybrid_results, lat_hybrid),
            ("Hybrid + Reranker", reranked_results, lat_reranker)
        ]

        for sys_name, res_list, lat in runs:
            metrics[sys_name]["latencies"].append(lat)
            rel_flags = [calculate_relevance(r, q_item) for r in res_list]

            if any(rel_flags[:1]):
                metrics[sys_name]["r1"] += 1
            if any(rel_flags[:3]):
                metrics[sys_name]["r3"] += 1
            if any(rel_flags[:5]):
                metrics[sys_name]["r5"] += 1

            # Precision@5
            p5 = sum(rel_flags[:5]) / 5.0
            metrics[sys_name]["p5"] += p5

            # MRR
            rank = 0
            for idx, flag in enumerate(rel_flags, 1):
                if flag:
                    rank = idx
                    break
            if rank > 0:
                metrics[sys_name]["mrr"] += 1.0 / rank

            # nDCG@5
            dcg = compute_dcg(rel_flags, 5)
            # Ideal DCG for 1 relevant item (or max relevant items)
            total_rel = max(1, sum(rel_flags[:5]))
            idcg = sum(1.0 / math.log2(i + 2) for i in range(min(total_rel, 5)))
            ndcg = (dcg / idcg) if idcg > 0 else 0.0
            metrics[sys_name]["ndcg5"] += ndcg

    total_q = len(benchmark_queries)

    header = f"{'System':<18} {'Recall@1':<10} {'Recall@3':<10} {'Recall@5':<10} {'MRR':<8} {'nDCG@5':<9} {'P@5':<7} {'Avg ms':<8} {'P50 ms':<8} {'P95 ms':<8}"
    print("\n" + "=" * len(header))
    print("PUBLICATION-READY HYBRID RETRIEVAL BENCHMARK")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    summary_export = {}
    for sys_name in systems:
        r1_pct = (metrics[sys_name]["r1"] / total_q) * 100.0
        r3_pct = (metrics[sys_name]["r3"] / total_q) * 100.0
        r5_pct = (metrics[sys_name]["r5"] / total_q) * 100.0
        mrr = metrics[sys_name]["mrr"] / total_q
        ndcg5 = metrics[sys_name]["ndcg5"] / total_q
        p5 = metrics[sys_name]["p5"] / total_q
        
        arr = np.array(metrics[sys_name]["latencies"])
        avg_lat = float(np.mean(arr))
        p50_lat = float(np.percentile(arr, 50))
        p95_lat = float(np.percentile(arr, 95))

        summary_export[sys_name] = {
            "recall_at_1": round(r1_pct, 1),
            "recall_at_3": round(r3_pct, 1),
            "recall_at_5": round(r5_pct, 1),
            "mrr": round(mrr, 3),
            "ndcg_at_5": round(ndcg5, 3),
            "precision_at_5": round(p5, 3),
            "avg_latency_ms": round(avg_lat, 1),
            "p50_latency_ms": round(p50_lat, 1),
            "p95_latency_ms": round(p95_lat, 1)
        }

        print(f"{sys_name:<18} {r1_pct:>8.1f}% {r3_pct:>8.1f}% {r5_pct:>8.1f}% {mrr:>7.3f} {ndcg5:>8.3f} {p5:>6.3f} {avg_lat:>7.1f} {p50_lat:>7.1f} {p95_lat:>7.1f}")

    print("-" * len(header))

    out_file = BASE_DIR / "data" / "reports" / "retrieval_benchmark_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_export, f, indent=2)

    print(f"Saved retrieval benchmark results to '{out_file}'.\n")

if __name__ == "__main__":
    run_benchmark()
