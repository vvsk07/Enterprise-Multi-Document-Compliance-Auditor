"""
Phase 7 Risk Engine Evaluation & Diagnostics Script.
Audits sample documents, calculates risk scores, generates reports, and displays diagnostic metrics.
"""

import sys
import os
import time
from pathlib import Path

# Add project root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, init_db
from app.models.document import Document
from app.services.document_processor import document_processor_service
from app.services.indexing_service import indexing_service
from app.services.compliance_engine import compliance_engine
from app.services.contradiction_service import contradiction_service
from app.services.risk_scoring_service import risk_scoring_service
from app.services.risk_recommendation_service import risk_recommendation_service
from app.services.audit_report_service import audit_report_service

def run_evaluation():
    print("=" * 80)
    print("PHASE 7 — EXPLAINABLE COMPLIANCE & RISK ENGINE EVALUATION")
    print("=" * 80)

    init_db()
    db = SessionLocal()

    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_documents"
    if not sample_dir.exists():
        print(f"Error: Sample directory '{sample_dir}' does not exist.")
        return

    sample_files = sorted(list(sample_dir.glob("*.txt")) + list(sample_dir.glob("*.pdf")))
    print(f"\n[1] Ingesting & Processing {len(sample_files)} sample document(s)...")

    start_time = time.time()
    ingested_docs = []

    for fpath in sample_files:
        existing = db.query(Document).filter(Document.filename == fpath.name).first()
        if not existing:
            doc_id = f"eval-{fpath.stem}"
            doc = Document(
                document_id=doc_id,
                filename=fpath.name,
                safe_filename=fpath.name,
                file_path=str(fpath.resolve()),
                file_type=fpath.suffix.replace(".", "").lower(),
                file_size=fpath.stat().st_size,
                document_status="UPLOADED"
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            document_processor_service.process_document(db, doc.document_id)
            indexing_service.index_document(db, doc.document_id)
            ingested_docs.append(doc)
        else:
            ingested_docs.append(existing)

    doc_ids = [d.document_id for d in ingested_docs]

    print(f"\n[2] Running Compliance Engine Audits across {len(doc_ids)} documents...")
    compliance_engine.evaluate_documents(db, doc_ids)

    print(f"\n[3] Running Cross-Document Contradiction Detection...")
    contradiction_service.find_contradictions(db, doc_ids)

    print(f"\n[4] Calculating Risk Assessments for {len(doc_ids)} documents...")
    for d_id in doc_ids:
        risk_scoring_service.calculate_document_risk(db, d_id)

    portfolio = risk_scoring_service.calculate_portfolio_risk(db, doc_ids)
    proc_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS & RISK METRICS")
    print("=" * 80)
    print(f"Total Documents Audited:         {portfolio.get('total_documents', 0)}")
    print(f"Portfolio Risk Score:            {portfolio.get('portfolio_risk_score', 0.0)} / 100")
    print(f"Portfolio Risk Level:            {portfolio.get('portfolio_risk_level', 'LOW')}")
    print(f"Average Document Risk Score:     {portfolio.get('average_risk_score', 0.0)}")
    print(f"Median Risk Score:               {portfolio.get('median_risk_score', 0.0)}")
    print(f"High / Critical Risk Documents:  {portfolio.get('high_risk_documents_count', 0) + portfolio.get('critical_risk_documents_count', 0)}")

    print("\nRisk Level Distribution:")
    for lvl, count in portfolio.get("risk_distribution", {}).items():
        print(f"  - {lvl:<10}: {count}")

    print("\nTop High-Risk Documents:")
    for idx, d_info in enumerate(portfolio.get("top_high_risk_documents", [])[:5], 1):
        print(f"  {idx}. {d_info['filename']} | Type: {d_info['document_type']} | Score: {d_info['risk_score']} ({d_info['risk_level']}) | Fails: {d_info['compliance_failures']} | Conflicts: {d_info['contradictions']}")

    print("\n[5] Testing Audit Report Generation...")
    json_report = audit_report_service.generate_json_audit_report(db, doc_ids)
    csv_report = audit_report_service.generate_csv_audit_report(db, export_type="risk_assessments")
    pdf_path = audit_report_service.generate_pdf_audit_report(db, document_ids=doc_ids)

    print(f"  - JSON Report Generated:       PASS (Keys: {len(json_report.keys())})")
    print(f"  - CSV Export Generated:        PASS ({len(csv_report.splitlines())} lines)")
    print(f"  - PDF Report Generated:        PASS ({pdf_path}, {os.path.getsize(pdf_path)} bytes)")
    print(f"  - Total Processing Time:       {proc_time:.3f}s")
    print("=" * 80)

    db.close()

if __name__ == "__main__":
    run_evaluation()
