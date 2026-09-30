"""
Contradiction Report Service.
Generates structured contradiction audit reports and aggregate metrics across multi-document repositories.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.document import Document, ContradictionFinding
from app.services.contradiction_service import contradiction_service

class ContradictionReportService:
    def get_contradictions_report(self, db: Session, document_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generates aggregate report and findings summary for cross-document contradictions.
        """
        if document_ids:
            findings = db.query(ContradictionFinding).filter(
                (ContradictionFinding.document_a_id.in_(document_ids)) |
                (ContradictionFinding.document_b_id.in_(document_ids))
            ).all()
            docs = db.query(Document).filter(Document.document_id.in_(document_ids)).all()
        else:
            findings = contradiction_service.get_all_contradictions(db)
            docs = db.query(Document).all()

        total_docs = len(docs)
        total_contradictions = len(findings)

        high_sev = sum(1 for f in findings if f.severity == "HIGH")
        med_sev = sum(1 for f in findings if f.severity == "MEDIUM")
        low_sev = sum(1 for f in findings if f.severity == "LOW")

        type_breakdown = {}
        affected_files = set()

        for f in findings:
            c_type = f.contradiction_type
            type_breakdown[c_type] = type_breakdown.get(c_type, 0) + 1
            if f.source_filename_a:
                affected_files.add(f.source_filename_a)
            if f.source_filename_b:
                affected_files.add(f.source_filename_b)

        return {
            "total_documents_analyzed": total_docs,
            "total_contradictions_detected": total_contradictions,
            "severity_metrics": {
                "high": high_sev,
                "medium": med_sev,
                "low": low_sev
            },
            "type_breakdown": type_breakdown,
            "affected_documents_count": len(affected_files),
            "affected_documents": list(affected_files),
            "contradictions": [f.to_dict() for f in findings]
        }

contradiction_report_service = ContradictionReportService()
