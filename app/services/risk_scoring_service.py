"""
Risk Scoring Service for Enterprise Compliance Auditor.
Provides deterministic, transparent, and explainable multi-component risk scoring for documents and portfolios.
"""

import uuid
import json
import logging
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document, ComplianceFinding, ContradictionFinding, RiskAssessment
from app.services.risk_recommendation_service import risk_recommendation_service

logger = logging.getLogger(__name__)

class RiskScoringService:
    def __init__(self):
        self._load_config()

    def _load_config(self):
        cfg = getattr(settings, "risk", {}) if hasattr(settings, "risk") else {}
        weights = cfg.get("weights", {})
        thresholds = cfg.get("thresholds", {})
        contradiction_cfg = cfg.get("contradiction", {})
        severity_cfg = cfg.get("severity", {})

        self.w_compliance = float(weights.get("compliance", 0.45))
        self.w_contradiction = float(weights.get("contradiction", 0.30))
        self.w_severity = float(weights.get("severity", 0.15))
        self.w_review = float(weights.get("review", 0.10))

        self.thresh_low = float(thresholds.get("low_max", 24.99))
        self.thresh_medium = float(thresholds.get("medium_max", 49.99))
        self.thresh_high = float(thresholds.get("high_max", 74.99))
        self.thresh_critical = float(thresholds.get("critical_max", 100.0))

        self.mult_confirmed = float(contradiction_cfg.get("confirmed_multiplier", 1.0))
        self.mult_potential = float(contradiction_cfg.get("potential_multiplier", 0.5))
        self.mult_reviewed = float(contradiction_cfg.get("reviewed_multiplier", 0.25))
        self.mult_dismissed = float(contradiction_cfg.get("dismissed_multiplier", 0.0))

        self.sev_high = float(severity_cfg.get("high", 1.0))
        self.sev_medium = float(severity_cfg.get("medium", 0.6))
        self.sev_low = float(severity_cfg.get("low", 0.3))

    def classify_risk_level(self, score: float) -> str:
        """
        Maps numeric score (0-100) to risk level string.
        """
        if score <= self.thresh_low:
            return "LOW"
        elif score <= self.thresh_medium:
            return "MEDIUM"
        elif score <= self.thresh_high:
            return "HIGH"
        else:
            return "CRITICAL"

    def calculate_document_risk(self, db: Session, document_id: str) -> Dict[str, Any]:
        """
        Calculates and persists explainable document risk assessment.
        """
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        compliance_findings = db.query(ComplianceFinding).filter(ComplianceFinding.document_id == document_id).all()
        contradiction_findings = db.query(ContradictionFinding).filter(
            (ContradictionFinding.document_a_id == document_id) |
            (ContradictionFinding.document_b_id == document_id)
        ).all()

        # 1. Compliance Risk Component (0-100)
        applicable_findings = [f for f in compliance_findings if f.status in ["PASS", "FAIL", "NEEDS_REVIEW"]]
        fail_findings = [f for f in compliance_findings if f.status == "FAIL"]
        review_findings = [f for f in compliance_findings if f.status == "NEEDS_REVIEW"]
        pass_findings = [f for f in compliance_findings if f.status == "PASS"]

        high_fails = [f for f in fail_findings if f.severity == "HIGH"]
        med_fails = [f for f in fail_findings if f.severity == "MEDIUM"]
        low_fails = [f for f in fail_findings if f.severity == "LOW"]

        if applicable_findings:
            raw_fail_points = (len(high_fails) * 100.0) + (len(med_fails) * 60.0) + (len(low_fails) * 30.0) + (len(review_findings) * 30.0)
            comp_raw_score = min(100.0, raw_fail_points / len(applicable_findings))
        else:
            comp_raw_score = 0.0

        # 2. Contradiction Risk Component (0-100)
        confirmed_contras = [c for c in contradiction_findings if c.status in ["CONFIRMED", "CONTRADICTION"]]
        potential_contras = [c for c in contradiction_findings if c.status == "POTENTIAL"]
        reviewed_contras = [c for c in contradiction_findings if c.status == "REVIEWED"]

        contra_points = 0.0
        for c in contradiction_findings:
            if c.status in ["DISMISSED", "NO_CONTRADICTION", "DIFFERENT_SCOPE"]:
                continue
            
            st_mult = self.mult_confirmed if c.status in ["CONFIRMED", "CONTRADICTION"] else (self.mult_potential if c.status == "POTENTIAL" else self.mult_reviewed)
            sv_mult = self.sev_high if c.severity == "HIGH" else (self.sev_medium if c.severity == "MEDIUM" else self.sev_low)
            conf = c.confidence or 0.85
            contra_points += (35.0 * st_mult * sv_mult * conf)

        contra_raw_score = min(100.0, contra_points)

        # 3. Severity Component (0-100)
        high_severity_total = len(high_fails) + len([c for c in contradiction_findings if c.severity == "HIGH" and c.status not in ["DISMISSED", "NO_CONTRADICTION"]])
        med_severity_total = len(med_fails) + len([c for c in contradiction_findings if c.severity == "MEDIUM" and c.status not in ["DISMISSED", "NO_CONTRADICTION"]])

        sev_raw_score = min(100.0, (high_severity_total * 40.0) + (med_severity_total * 20.0))

        # 4. Review / Uncertainty Component (0-100)
        review_raw_score = min(100.0, (len(review_findings) * 25.0) + (len(potential_contras) * 25.0))

        # Final Weighted Calculation
        final_score = (
            (comp_raw_score * self.w_compliance) +
            (contra_raw_score * self.w_contradiction) +
            (sev_raw_score * self.w_severity) +
            (review_raw_score * self.w_review)
        )
        final_score = round(min(100.0, max(0.0, final_score)), 2)
        risk_level = self.classify_risk_level(final_score)

        # Generate Human-Readable Risk Factors
        risk_factors = []
        if len(high_fails) > 0:
            risk_factors.append(f"{len(high_fails)} HIGH severity compliance rule(s) failed.")
        if len(med_fails) > 0:
            risk_factors.append(f"{len(med_fails)} MEDIUM severity compliance rule(s) failed.")
        if len(confirmed_contras) > 0:
            topics = set(c.topic for c in confirmed_contras)
            risk_factors.append(f"{len(confirmed_contras)} confirmed cross-document contradiction(s) detected regarding '{', '.join(topics)}'.")
        if len(potential_contras) > 0:
            risk_factors.append(f"{len(potential_contras)} potential cross-document contradiction(s) require review.")
        if len(review_findings) > 0:
            risk_factors.append(f"{len(review_findings)} compliance rule(s) require manual legal review.")
        if not risk_factors:
            risk_factors.append("No critical compliance failures or document contradictions detected.")

        # Generate Actionable Recommendations
        recommendations = risk_recommendation_service.generate_recommendations(
            db, document_id, compliance_findings, contradiction_findings
        )

        components_dict = {
            "compliance": {
                "raw_score": round(comp_raw_score, 2),
                "weight": self.w_compliance,
                "weighted_score": round(comp_raw_score * self.w_compliance, 2),
                "applicable_rules": len(applicable_findings),
                "passed_rules": len(pass_findings),
                "failed_rules": len(fail_findings),
                "review_rules": len(review_findings)
            },
            "contradiction": {
                "raw_score": round(contra_raw_score, 2),
                "weight": self.w_contradiction,
                "weighted_score": round(contra_raw_score * self.w_contradiction, 2),
                "confirmed": len(confirmed_contras),
                "potential": len(potential_contras),
                "reviewed": len(reviewed_contras)
            },
            "severity": {
                "raw_score": round(sev_raw_score, 2),
                "weight": self.w_severity,
                "weighted_score": round(sev_raw_score * self.w_severity, 2),
                "high_severity_count": high_severity_total,
                "medium_severity_count": med_severity_total
            },
            "review": {
                "raw_score": round(review_raw_score, 2),
                "weight": self.w_review,
                "weighted_score": round(review_raw_score * self.w_review, 2),
                "pending_reviews": len(review_findings) + len(potential_contras)
            }
        }

        # Persist or update RiskAssessment in DB
        assessment = db.query(RiskAssessment).filter(RiskAssessment.document_id == document_id).first()
        if not assessment:
            assessment = RiskAssessment(
                risk_assessment_id=str(uuid.uuid4()),
                document_id=document_id
            )

        assessment.risk_score = final_score
        assessment.risk_level = risk_level
        assessment.compliance_score = comp_raw_score
        assessment.contradiction_score = contra_raw_score
        assessment.severity_score = sev_raw_score
        assessment.review_score = review_raw_score
        assessment.compliance_weight = self.w_compliance
        assessment.contradiction_weight = self.w_contradiction
        assessment.severity_weight = self.w_severity
        assessment.review_weight = self.w_review
        assessment.high_findings_count = len(high_fails)
        assessment.medium_findings_count = len(med_fails)
        assessment.low_findings_count = len(low_fails)
        assessment.compliance_fail_count = len(fail_findings)
        assessment.compliance_review_count = len(review_findings)
        assessment.confirmed_contradiction_count = len(confirmed_contras)
        assessment.potential_contradiction_count = len(potential_contras)
        assessment.risk_factors_json = json.dumps(risk_factors)
        assessment.recommendations_json = json.dumps(recommendations)
        assessment.components_breakdown_json = json.dumps(components_dict)
        assessment.calculation_version = "1.0"
        assessment.updated_at = datetime.now(timezone.utc)

        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        res_dict = assessment.to_dict()
        res_dict["filename"] = doc.filename
        res_dict["predicted_document_type"] = doc.predicted_document_type or "Unclassified"
        return res_dict

    def calculate_portfolio_risk(self, db: Session, document_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Calculates aggregate portfolio / organization level risk statistics.
        """
        query = db.query(Document)
        if document_ids:
            query = query.filter(Document.document_id.in_(document_ids))
        docs = query.all()

        if not docs:
            return {
                "total_documents": 0,
                "average_risk_score": 0.0,
                "portfolio_risk_score": 0.0,
                "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
                "high_risk_documents_count": 0,
                "critical_risk_documents_count": 0,
                "top_high_risk_documents": [],
                "most_frequent_failed_rules": [],
                "most_frequent_contradiction_topics": []
            }

        assessments = []
        for d in docs:
            ass = db.query(RiskAssessment).filter(RiskAssessment.document_id == d.document_id).first()
            if not ass:
                ass_dict = self.calculate_document_risk(db, d.document_id)
            else:
                ass_dict = ass.to_dict()
                ass_dict["filename"] = d.filename
                ass_dict["predicted_document_type"] = d.predicted_document_type or "Unclassified"
            assessments.append(ass_dict)

        scores = [a["risk_score"] for a in assessments]
        avg_score = round(float(np.mean(scores)), 2) if scores else 0.0
        median_score = round(float(np.median(scores)), 2) if scores else 0.0

        # Weighted portfolio score based on applicable rules count
        weights = []
        weighted_scores = []
        for a in assessments:
            app_cnt = a.get("components", {}).get("compliance", {}).get("applicable_rules", 1)
            w = max(1, app_cnt)
            weights.append(w)
            weighted_scores.append(a["risk_score"] * w)

        weighted_portfolio_score = round(sum(weighted_scores) / sum(weights), 2) if weights else avg_score

        dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for a in assessments:
            lvl = a["risk_level"]
            dist[lvl] = dist.get(lvl, 0) + 1

        top_docs = sorted(assessments, key=lambda x: x["risk_score"], reverse=True)[:10]

        # Aggregate Rule Failures
        rule_counts: Dict[str, int] = {}
        for d in docs:
            fails = db.query(ComplianceFinding).filter(ComplianceFinding.document_id == d.document_id, ComplianceFinding.status == "FAIL").all()
            for f in fails:
                rule_counts[f.rule_id] = rule_counts.get(f.rule_id, 0) + 1

        top_failed_rules = sorted([{"rule_id": k, "failure_count": v} for k, v in rule_counts.items()], key=lambda x: x["failure_count"], reverse=True)[:5]

        # Aggregate Contradiction Topics
        topic_counts: Dict[str, int] = {}
        all_contras = db.query(ContradictionFinding).filter(ContradictionFinding.status.in_(["CONFIRMED", "POTENTIAL", "CONTRADICTION"])).all()
        for c in all_contras:
            topic_counts[c.topic] = topic_counts.get(c.topic, 0) + 1

        top_contradiction_topics = sorted([{"topic": k, "contradiction_count": v} for k, v in topic_counts.items()], key=lambda x: x["contradiction_count"], reverse=True)[:5]

        return {
            "total_documents": len(docs),
            "average_risk_score": avg_score,
            "median_risk_score": median_score,
            "portfolio_risk_score": weighted_portfolio_score,
            "portfolio_risk_level": self.classify_risk_level(weighted_portfolio_score),
            "risk_distribution": dist,
            "high_risk_documents_count": dist.get("HIGH", 0),
            "critical_risk_documents_count": dist.get("CRITICAL", 0),
            "top_high_risk_documents": [
                {
                    "document_id": a["document_id"],
                    "filename": a.get("filename", ""),
                    "document_type": a.get("predicted_document_type", "Unclassified"),
                    "risk_score": a["risk_score"],
                    "risk_level": a["risk_level"],
                    "compliance_failures": a.get("compliance_fail_count", 0),
                    "contradictions": a.get("confirmed_contradiction_count", 0) + a.get("potential_contradiction_count", 0)
                } for a in top_docs
            ],
            "most_frequent_failed_rules": top_failed_rules,
            "most_frequent_contradiction_topics": top_contradiction_topics
        }

    def get_risk_breakdown(self, db: Session, document_id: str) -> Dict[str, Any]:
        """
        Retrieves stored or computes risk assessment breakdown.
        """
        ass = db.query(RiskAssessment).filter(RiskAssessment.document_id == document_id).first()
        if not ass:
            return self.calculate_document_risk(db, document_id)
        
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        res_dict = ass.to_dict()
        if doc:
            res_dict["filename"] = doc.filename
            res_dict["predicted_document_type"] = doc.predicted_document_type or "Unclassified"
        return res_dict

    def recalculate_all_risks(self, db: Session) -> Dict[str, Any]:
        """
        Recalculates risk assessment for all ingested documents in database.
        """
        docs = db.query(Document).all()
        updated = []
        for d in docs:
            res = self.calculate_document_risk(db, d.document_id)
            updated.append(res)
        return {
            "status": "success",
            "message": f"Successfully recalculated risk scores for {len(updated)} document(s).",
            "recalculated_count": len(updated)
        }


risk_scoring_service = RiskScoringService()
