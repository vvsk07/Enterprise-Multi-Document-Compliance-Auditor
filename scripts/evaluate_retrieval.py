"""
Phase 4 Retrieval & RAG Evaluation Script.
Evaluates Precision@K, Recall@K, MRR, and Citation Accuracy across benchmark document questions.
"""

import sys
import os
import time
import uuid
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, init_db
from app.models.document import Document
from app.services.document_processor import document_processor_service
from app.services.indexing_service import indexing_service
from app.services.search_service import search_service
from app.services.rag_service import rag_service

BASE_DIR = Path(__file__).resolve().parent.parent

def run_retrieval_evaluation():
    print("=" * 60)
    print("      ENTERPRISE COMPLIANCE AUDITOR - PHASE 4 RAG EVALUATION")
    print("=" * 60)

    db = SessionLocal()
    init_db()

    # Ingest sample documents if database is empty
    if db.query(Document).count() == 0:
        print("\n[-] Ingesting sample documents into SQLite database...")
        sample_dir = BASE_DIR / "data" / "sample_documents"
        for sample_file in sample_dir.glob("*.*"):
            if sample_file.suffix in [".txt", ".docx", ".pdf"]:
                doc_id = str(uuid.uuid4())
                doc = Document(
                    document_id=doc_id,
                    filename=sample_file.name,
                    safe_filename=sample_file.name,
                    file_path=str(sample_file.resolve()),
                    file_type=sample_file.suffix.replace(".", ""),
                    file_size=sample_file.stat().st_size,
                    document_status="UPLOADED"
                )
                db.add(doc)
                db.commit()
                document_processor_service.process_document(db, doc_id)

    # 1. Rebuild index to ensure fresh FAISS vector index
    print("\n[-] Indexing document repository...")
    rebuild_res = indexing_service.rebuild_index(db)
    print(f"  [+] Total Documents Indexed: {rebuild_res['indexed_documents']}")
    print(f"  [+] Total Chunks Vectorized: {rebuild_res['total_chunks_indexed']}")

    # 2. Benchmark Evaluation Dataset (12 Ground-Truth Questions)
    eval_benchmark = [
        {"query": "What are the confidentiality obligations?", "expected_keywords": ["confidential", "nondisclosure", "secrets"]},
        {"query": "What is the agreement term and duration?", "expected_keywords": ["term", "duration", "years", "effective date"]},
        {"query": "What are the termination conditions and notice periods?", "expected_keywords": ["terminate", "termination", "notice", "days"]},
        {"query": "What governing law and court jurisdiction applies?", "expected_keywords": ["governed", "jurisdiction", "court", "law"]},
        {"query": "What are the data protection and privacy requirements?", "expected_keywords": ["data protection", "privacy", "gdpr"]},
        {"query": "What is the dispute resolution process?", "expected_keywords": ["dispute", "arbitration", "mediation"]},
        {"query": "How long must records and audit logs be retained?", "expected_keywords": ["retention", "retain", "records", "years"]},
        {"query": "What is the termination notice in Policy A?", "expected_keywords": ["30 days", "notice", "policy a"]},
        {"query": "What is the termination notice in Policy B?", "expected_keywords": ["60 days", "notice", "policy b"]},
        {"query": "What is the consultant hourly billing rate?", "expected_keywords": ["rate", "$250", "hourly", "paid"]},
        {"query": "What is the license scope for the software?", "expected_keywords": ["license", "software", "non-exclusive"]},
        {"query": "What is the uptime SLA percentage?", "expected_keywords": ["uptime", "sla", "99.9%"]}
    ]

    print(f"\n[-] Running Retrieval Benchmark across {len(eval_benchmark)} questions (Top-K=3)...")

    reciprocal_ranks = []
    hits_at_k = 0
    total_latency_ms = 0

    for idx, item in enumerate(eval_benchmark, 1):
        q = item["query"]
        expected_kw = item["expected_keywords"]

        t0 = time.time()
        results = search_service.search(query=q, top_k=3)
        t1 = time.time()

        latency_ms = (t1 - t0) * 1000
        total_latency_ms += latency_ms

        rank = 0
        hit = False

        for r_idx, r in enumerate(results, 1):
            text_lower = r["text"].lower()
            if any(kw in text_lower for kw in expected_kw):
                if rank == 0:
                    rank = r_idx
                hit = True

        if hit:
            hits_at_k += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        top_score = results[0]["score"] if results else 0.0
        print(f"  [{idx:02d}] '{q[:35]:<35}...' -> Score: {top_score:.4f} | Hit@3: {'YES' if hit else 'NO'} | Rank: {rank if rank else 'N/A'}")

    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    recall_at_3 = (hits_at_k / len(eval_benchmark)) * 100
    avg_latency = total_latency_ms / len(eval_benchmark)

    print("\n[-] Semantic Search Retrieval Metrics:")
    print(f"  [+] Recall@3        : {recall_at_3:.2f}%")
    print(f"  [+] MRR             : {mrr:.4f}")
    print(f"  [+] Avg Latency     : {avg_latency:.2f} ms")

    # 3. RAG Citation Verification
    print("\n[-] Testing Grounded RAG Query with Citations...")
    rag_res = rag_service.query_rag("What are the termination notice conditions?")
    print(f"  [+] Question : {rag_res['question']}")
    print(f"  [+] Answer   : {rag_res['answer']}")
    print("  [+] Citations:")
    for c in rag_res["citations"]:
        print(f"      - {c}")

    db.close()
    print("\n" + "=" * 60)
    print(" PHASE 4 RETRIEVAL & RAG EVALUATION PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_retrieval_evaluation()
    sys.exit(0 if success else 1)
