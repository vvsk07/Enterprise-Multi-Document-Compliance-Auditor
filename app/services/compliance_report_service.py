"""
Compliance Report Service.
Generates document-level and multi-document compliance summaries and structured audit reports.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document, ComplianceFinding

class ComplianceReportService:
    def get_document_summary(self, db: Session, document_id: str) -> Dict[str, Any]:
        """
        Generates summary statistics and findings breakdown for a single document.
        """
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        findings = db.query(ComplianceFinding).filter(ComplianceFinding.document_id == document_id).all()
        
        passed_count = sum(1 for f in findings if f.status == "PASS")
        failed_count = sum(1 for f in findings if f.status == "FAIL")
        review_count = sum(1 for f in findings if f.status == "NEEDS_REVIEW")
        na_count = sum(1 for f in findings if f.status == "NOT_APPLICABLE")
        total_rules = len(findings)
        applicable_rules = total_rules - na_count

        return {
            "document_id": doc.document_id,
            "document_name": doc.filename,
            "document_type": doc.predicted_document_type or "Unclassified",
            "total_rules": total_rules,
            "applicable_rules": applicable_rules,
            "passed": passed_count,
            "failed": failed_count,
            "needs_review": review_count,
            "not_applicable": na_count,
            "findings": [f.to_dict() for f in findings]
        }

    def get_multi_document_report(self, db: Session, document_ids: List[str]) -> Dict[str, Any]:
        """
        Generates aggregate compliance summary for a list of document IDs.
        """
        document_summaries = []
        total_docs = len(document_ids)
        total_passed = 0
        total_failed = 0
        total_review = 0
        total_na = 0

        for doc_id in document_ids:
            try:
                summary = self.get_document_summary(db, doc_id)
                document_summaries.append(summary)
                total_passed += summary["passed"]
                total_failed += summary["failed"]
                total_review += summary["needs_review"]
                total_na += summary["not_applicable"]
            except Exception:
                continue

        return {
            "total_documents": total_docs,
            "audited_documents": len(document_summaries),
            "aggregate_metrics": {
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_needs_review": total_review,
                "total_not_applicable": total_na
            },
            "document_summaries": document_summaries
        }

compliance_report_service = ComplianceReportService()
