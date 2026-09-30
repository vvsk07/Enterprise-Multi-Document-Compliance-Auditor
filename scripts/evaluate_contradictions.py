"""
Cross-Document Contradiction Detection Evaluation Script.
Audits contradictory_policy_a.txt vs contradictory_policy_b.txt and other repository documents
to evaluate contradiction identification, fact extraction, and canonical evidence tracking.
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
from app.services.contradiction_service import contradiction_service
from app.services.contradiction_report_service import contradiction_report_service

SAMPLE_DOCS_DIR = BASE_DIR / "data" / "sample_documents"

def run_contradiction_evaluation():
    print("=" * 75)
    print("PHASE 6: CROSS-DOCUMENT CONTRADICTION DETECTION EVALUATION")
    print("=" * 75)
    print("Environment: Windows 11 | Python 3.14.6 | CPU-only | SQLite DB")
    print("Disclaimer: Demonstration evaluation dataset (small sample size).")
    print("-" * 75)

    init_db()
    db: Session = SessionLocal()

    sample_files = [
        "contradictory_policy_a.txt",
        "contradictory_policy_b.txt",
        "compliant_contract.txt"
    ]

    processed_docs: List[Document] = []
    
    # 1. Ingest & Index Sample Documents
    print(f"\n[1/3] Ingesting and indexing {len(sample_files)} evaluation documents...")
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
        print(f"  [OK] {filename:<30} | Category: {processed_doc.predicted_document_type or 'Unclassified':<15} | Chunks: {len(processed_doc.chunks)}")

    # 2. Run Cross-Document Contradiction Analysis
    doc_ids = [d.document_id for d in processed_docs]
    print(f"\n[2/3] Analyzing candidate chunk pairs across {len(doc_ids)} documents...")
    
    findings = contradiction_service.detect_contradictions(db, doc_ids)
    report = contradiction_report_service.get_contradictions_report(db, doc_ids)

    # 3. Print Results Summary & Details
    print("\n[3/3] CONTRADICTION DETECTION RESULTS")
    print("-" * 75)
    print(f"  * Total Documents Analyzed      : {report['total_documents_analyzed']}")
    print(f"  * Total Contradictions Found    : {report['total_contradictions_detected']}")
    print(f"  * High Severity Contradictions : {report['severity_metrics']['high']}")
    print(f"  * Medium Severity Contradictions: {report['severity_metrics']['medium']}")
    print(f"  * Affected Documents Count      : {report['affected_documents_count']}")
    print("-" * 75)

    if findings:
        print("\nDETAILED CONTRADICTION FINDINGS:")
        print("=" * 75)

        for idx, f in enumerate(findings, 1):
            f_dict = f.to_dict()
            print(f"\nFinding #{idx}: [CONTRADICTION DETECTED]")
            print(f"  Topic             : {f_dict['topic']}")
            print(f"  Contradiction Type: {f_dict['contradiction_type']}")
            print(f"  Severity          : {f_dict['severity']}")
            print(f"  Confidence Score  : {f_dict['confidence']:.2%}")
            print(f"  Explanation       : {f_dict['explanation']}")
            print(f"  --------------------------------------------------")
            print(f"  Document A        : {f_dict['source_filename_a']} (Page {f_dict['page_a'] or 'N/A'}, Section: {f_dict['section_a'] or 'General'})")
            print(f"  Value A           : {f_dict['value_a']} {f_dict['unit'] or ''}")
            print(f"  Evidence A        : \"{f_dict['statement_a'][:140]}\"")
            print(f"  --------------------------------------------------")
            print(f"  Document B        : {f_dict['source_filename_b']} (Page {f_dict['page_b'] or 'N/A'}, Section: {f_dict['section_b'] or 'General'})")
            print(f"  Value B           : {f_dict['value_b']} {f_dict['unit'] or ''}")
            print(f"  Evidence B        : \"{f_dict['statement_b'][:140]}\"")
            print(f"  --------------------------------------------------")

    db.close()
    print("\nEvaluation completed successfully.")

if __name__ == "__main__":
    run_contradiction_evaluation()
