"""
System Latency & Performance Benchmark Script.
Measures Avg, P50, and P95 execution latencies across retrieval, RAG, compliance auditing,
contradiction scanning, and risk calculation engines.
"""

import sys
import time
import json
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal
from app.services.indexing_service import indexing_service
from app.services.vector_store import vector_store
from app.services.bm25_service import bm25_service
from app.services.embedding_service import embedding_service
from app.services.hybrid_search_service import hybrid_search_service
from app.services.reranker_service import reranker_service
from app.services.advanced_rag_service import advanced_rag_service
from app.services.compliance_engine import compliance_engine
from app.services.contradiction_service import contradiction_service
from app.services.risk_scoring_service import risk_scoring_service
from app.models.document import Document

def run_performance_benchmark(num_iterations: int = 5):
    print("\nInitializing database index for performance benchmark...")
    db = SessionLocal()
    indexing_service.rebuild_index(db)

    docs = db.query(Document).all()
    if not docs:
        print("No documents found in database. Ingesting sample document...")
        sample_file = BASE_DIR / "data" / "sample_documents" / "compliant_contract.txt"
        if sample_file.exists():
            from app.services.document_processor import document_processor_service
            with open(sample_file, "rb") as f:
                content = f.read()
            doc_id = "bench-doc-001"
            document_processor_service.process_document(
                db=db,
                document_id=doc_id,
                filename="compliant_contract.txt",
                safe_filename="compliant_contract.txt",
                file_path=str(sample_file),
                file_type="txt",
                file_size=len(content),
                file_bytes=content
            )
            indexing_service.index_document(db, doc_id)
            docs = db.query(Document).all()

    doc_id = docs[0].document_id if docs else "bench-doc"

    query = "What is the vendor termination notice period?"

    benchmarks = {
        "FAISS search": [],
        "BM25 search": [],
        "Hybrid search": [],
        "Cross encoder": [],
        "RAG": [],
        "Compliance audit": [],
        "Contradiction detection": [],
        "Risk calculation": []
    }

    # Warmup models
    _ = embedding_service.embed_single(query)
    _ = reranker_service.rerank(query, [{"text": "sample chunk text"}], top_k=1)

    print(f"Running benchmark iterations ({num_iterations} runs)...")

    for _ in range(num_iterations):
        # 1. FAISS search
        t0 = time.time()
        q_vec = embedding_service.embed_single(query)
        _ = vector_store.similarity_search(q_vec, top_k=5)
        benchmarks["FAISS search"].append((time.time() - t0) * 1000.0)

        # 2. BM25 search
        t0 = time.time()
        _ = bm25_service.search(query, top_k=5)
        benchmarks["BM25 search"].append((time.time() - t0) * 1000.0)

        # 3. Hybrid search
        t0 = time.time()
        cands = hybrid_search_service.search(query, top_k=20)
        benchmarks["Hybrid search"].append((time.time() - t0) * 1000.0)

        # 4. Cross encoder
        t0 = time.time()
        _ = reranker_service.rerank(query, cands, top_k=5)
        benchmarks["Cross encoder"].append((time.time() - t0) * 1000.0)

        # 5. RAG
        t0 = time.time()
        _ = advanced_rag_service.query(query, top_k=5)
        benchmarks["RAG"].append((time.time() - t0) * 1000.0)

        # 6. Compliance audit
        t0 = time.time()
        _ = compliance_engine.evaluate_document(db, doc_id)
        benchmarks["Compliance audit"].append((time.time() - t0) * 1000.0)

        # 7. Contradiction detection
        t0 = time.time()
        _ = contradiction_service.detect_contradictions(db)
        benchmarks["Contradiction detection"].append((time.time() - t0) * 1000.0)


        # 8. Risk calculation
        t0 = time.time()
        _ = risk_scoring_service.calculate_document_risk(db, doc_id)
        benchmarks["Risk calculation"].append((time.time() - t0) * 1000.0)

    db.close()

    print("\n" + "=" * 60)
    print("PHASE 8 PERFORMANCE BENCHMARK")
    print("=" * 60)
    print(f"{'Operation':<30} {'Avg ms':<10} {'P50 ms':<10} {'P95 ms':<10}")
    print("-" * 60)

    results_export = {}
    for op_name, lats in benchmarks.items():
        arr = np.array(lats)
        avg = float(np.mean(arr))
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))

        results_export[op_name] = {
            "avg_ms": round(avg, 1),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1)
        }

        print(f"{op_name:<30} {avg:>8.1f}   {p50:>8.1f}   {p95:>8.1f}")

    print("-" * 60)

    out_file = BASE_DIR / "data" / "reports" / "performance_benchmark_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_export, f, indent=2)

    print(f"Performance benchmark saved to '{out_file}'.\n")

if __name__ == "__main__":
    run_performance_benchmark()
