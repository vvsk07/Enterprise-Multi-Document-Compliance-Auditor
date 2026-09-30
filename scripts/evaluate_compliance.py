"""
Compliance Engine Evaluation Script.
Evaluates the Compliance Rule Engine against sample business documents in data/sample_documents/
and outputs detailed compliance metrics, rule accuracy, and finding status counts.
"""

import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.document import Document
from app.services.document_processor import document_processor_service
from app.services.indexing_service import indexing_service
from app.services.compliance_engine import compliance_engine
from app.services.compliance_report_service import compliance_report_service

SAMPLE_DOCS_DIR = BASE_DIR / "data" / "sample_documents"

def run_compliance_evaluation():
    print("=" * 70)
    print("PHASE 5: COMPLIANCE RULE ENGINE EVALUATION")
    print("=" * 70)
    print("Environment: Windows 11 | Python 3.14.6 | CPU-only | SQLite DB")
    print("Disclaimer: Demonstration evaluation dataset (small sample size).")
    print("-" * 70)

    init_db()
    db: Session = SessionLocal()

    sample_files = [
        "compliant_contract.txt",
        "missing_clauses_contract.txt",
        "contradictory_policy_a.txt",
        "contradictory_policy_b.txt",
        "sample_contract.docx",
        "sample_policy.pdf"
    ]

    processed_docs: List[Document] = []
    
    # 1. Ingest & Index Sample Documents
    print(f"\n[1/3] Ingesting and indexing {len(sample_files)} sample documents...")
    for filename in sample_files:
        file_path = SAMPLE_DOCS_DIR / filename
        if not file_path.exists():
            print(f"  [SKIP] File not found: {filename}")
            continue

        existing_doc = db.query(Document).filter(Document.filename == filename).first()
        if existing_doc:
            doc_id = existing_doc.document_id
        else:
            doc_id = str(uuid.uuid4())
            file_ext = file_path.suffix.lower().replace(".", "")
            file_size = file_path.stat().st_size
            doc = Document(
                document_id=doc_id,
                filename=filename,
                safe_filename=filename,
                file_path=str(file_path.resolve()),
                file_type=file_ext,
                file_size=file_size,
                document_status="UPLOADED"
            )
            db.add(doc)
            db.commit()

        processed_doc = document_processor_service.process_document(db, doc_id)
        indexing_service.index_document(db, doc_id)
        processed_docs.append(processed_doc)
        print(f"  [OK] {filename:<30} | Type: {processed_doc.predicted_document_type or 'Unclassified':<15} | Chunks: {len(processed_doc.chunks)}")

    # 2. Run Compliance Audit
    print(f"\n[2/3] Running compliance audits across {len(processed_docs)} documents...")
    all_summaries = []
    total_rule_evals = 0
    total_pass = 0
    total_fail = 0
    total_review = 0
    total_na = 0

    for doc in processed_docs:
        compliance_engine.evaluate_document(db, doc.document_id)
        summary = compliance_report_service.get_document_summary(db, doc.document_id)
        all_summaries.append(summary)

        total_rule_evals += summary["total_rules"]
        total_pass += summary["passed"]
        total_fail += summary["failed"]
        total_review += summary["needs_review"]
        total_na += summary["not_applicable"]

    # 3. Print Results Summary Table
    print("\n[3/3] EVALUATION RESULTS BY DOCUMENT")
    print("-" * 85)
    print(f"{'Filename':<30} | {'Type':<18} | {'PASS':<6} | {'FAIL':<6} | {'REVIEW':<6} | {'N/A':<4}")
    print("-" * 85)

    for s in all_summaries:
        print(f"{s['document_name']:<30} | {s['document_type']:<18} | {s['passed']:<6} | {s['failed']:<6} | {s['needs_review']:<6} | {s['not_applicable']:<4}")

    print("-" * 85)
    print("AGGREGATE METRICS:")
    print(f"  * Total Documents Audited   : {len(all_summaries)}")
    print(f"  * Total Rule Evaluations    : {total_rule_evals}")
    print(f"  * PASS Findings [PASS]      : {total_pass} ({total_pass/total_rule_evals:.1%})")
    print(f"  * FAIL Findings [FAIL]      : {total_fail} ({total_fail/total_rule_evals:.1%})")
    print(f"  * NEEDS REVIEW [REVIEW]     : {total_review} ({total_review/total_rule_evals:.1%})")
    print(f"  * NOT APPLICABLE [N/A]       : {total_na} ({total_na/total_rule_evals:.1%})")
    
    applicable_evals = total_rule_evals - total_na
    if applicable_evals > 0:
        decisive_rate = (total_pass + total_fail) / applicable_evals
        print(f"  * Decisive Determination Rate: {decisive_rate:.1%} (PASS/FAIL vs Applicable)")
    
    print("\n" + "=" * 70)
    print("SAMPLE COMPLIANCE FINDINGS DETAILS:")
    print("=" * 70)

    # Display sample detailed findings for compliant_contract vs missing_clauses_contract
    for s in all_summaries:
        if s['document_name'] in ['compliant_contract.txt', 'missing_clauses_contract.txt']:
            print(f"\nDocument: {s['document_name']}")
            for f in s['findings'][:4]:  # First 4 findings
                badge = "[PASS]" if f['status'] == "PASS" else "[FAIL]" if f['status'] == "FAIL" else "[REVIEW]"
                print(f"  {badge} {f['rule_id']} - {f['title']}")
                print(f"    Explanation: {f['explanation']}")
                if f.get('evidence_text'):
                    snippet = f['evidence_text'][:120].replace('\n', ' ')
                    print(f"    Evidence: \"{snippet}...\"")

    db.close()
    print("\nEvaluation completed successfully.")

if __name__ == "__main__":
    run_compliance_evaluation()
