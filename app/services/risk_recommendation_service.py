"""
Risk Recommendation Service for Enterprise Compliance Auditor.
Generates deterministic, evidence-grounded recommendations for compliance failures and contradictions.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, ComplianceFinding, ContradictionFinding

logger = logging.getLogger(__name__)

class RiskRecommendationService:
    def generate_recommendations(
        self,
        db: Session,
        document_id: str,
        compliance_findings: Optional[List[ComplianceFinding]] = None,
        contradiction_findings: Optional[List[ContradictionFinding]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates structured, explainable recommendations for a document based on database evidence.
        """
        if compliance_findings is None:
            compliance_findings = db.query(ComplianceFinding).filter(ComplianceFinding.document_id == document_id).all()

        if contradiction_findings is None:
            contradiction_findings = db.query(ContradictionFinding).filter(
                (ContradictionFinding.document_a_id == document_id) |
                (ContradictionFinding.document_b_id == document_id)
            ).all()

        recommendations = []
        rec_id_counter = 1

        # 1. Generate Recommendations for Failed Compliance Rules
        for f in compliance_findings:
            if f.status == "FAIL":
                priority = f.severity or "MEDIUM"
                rem_text = f.remediation or f"Review {f.title} requirement and update document to include missing mandatory provisions."
                recommendations.append({
                    "recommendation_id": f"REC-{rec_id_counter:03d}",
                    "priority": priority,
                    "title": f"Resolve Compliance Failure: {f.title}",
                    "recommendation": f"Address {f.rule_id} ({f.title}). {rem_text}",
                    "source": f.rule_id,
                    "finding_id": f.finding_id,
                    "finding_type": "COMPLIANCE_FAILURE",
                    "status": "OPEN"
                })
                rec_id_counter += 1
            elif f.status == "NEEDS_REVIEW":
                recommendations.append({
                    "recommendation_id": f"REC-{rec_id_counter:03d}",
                    "priority": "LOW",
                    "title": f"Review Required: {f.title}",
                    "recommendation": f"Perform legal review for {f.rule_id} ({f.title}). Evidence requires human verification.",
                    "source": f.rule_id,
                    "finding_id": f.finding_id,
                    "finding_type": "COMPLIANCE_REVIEW",
                    "status": "OPEN"
                })
                rec_id_counter += 1

        # 2. Generate Recommendations for Contradictions
        for c in contradiction_findings:
            if c.status in ["CONFIRMED", "POTENTIAL", "CONTRADICTION"]:
                priority = "HIGH" if c.severity == "HIGH" or c.status == "CONFIRMED" else "MEDIUM"
                other_doc_name = c.source_filename_b if c.document_a_id == document_id else c.source_filename_a
                expl_summary = c.explanation.split(".")[0] if c.explanation else f"Conflict detected on topic '{c.topic}'"

                recommendations.append({
                    "recommendation_id": f"REC-{rec_id_counter:03d}",
                    "priority": priority,
                    "title": f"Reconcile Policy Conflict: {c.topic}",
                    "recommendation": f"Reconcile {c.contradiction_type} regarding '{c.topic}' with '{other_doc_name or 'related policy'}'. {expl_summary}.",
                    "source": c.contradiction_type,
                    "finding_id": c.contradiction_id,
                    "finding_type": "CONTRADICTION",
                    "status": "OPEN"
                })
                rec_id_counter += 1

        logger.info(f"Generated {len(recommendations)} recommendations for document '{document_id}'.")
        return recommendations


risk_recommendation_service = RiskRecommendationService()
