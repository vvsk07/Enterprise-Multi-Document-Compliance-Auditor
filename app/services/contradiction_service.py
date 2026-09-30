"""
Cross-Document Contradiction Detection Service.
Identifies conflicting factual and policy statements across documents without requiring generative LLMs.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings, yaml_config
from app.models.document import Document, DocumentChunk, ContradictionFinding, CrossDocumentContradiction
from app.services.fact_extraction_service import fact_extraction_service
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

class ContradictionDetectionService:
    def __init__(self):
        contradiction_config = yaml_config.get("contradiction", {})
        self.enabled = contradiction_config.get("enabled", True)
        self.candidate_threshold = float(contradiction_config.get("semantic_similarity_threshold", contradiction_config.get("candidate_similarity_threshold", 0.65)))
        self.contradiction_threshold = float(contradiction_config.get("contradiction_threshold", 0.70))
        self.potential_threshold = float(contradiction_config.get("potential_threshold", 0.50))
        self.max_candidates = int(contradiction_config.get("max_candidates_per_chunk", 5))

        weights = contradiction_config.get("weights", {})
        self.w_semantic = float(weights.get("semantic", 0.35))
        self.w_numeric = float(weights.get("numeric", 0.25))
        self.w_negation = float(weights.get("negation", 0.20))
        self.w_keyword = float(weights.get("keyword", 0.10))
        self.w_domain = float(weights.get("domain_rule", 0.10))

    def _canonical_key(self, doc_a_id: str, chunk_a_id: str, doc_b_id: str, chunk_b_id: str, topic: str) -> str:
        """
        Generates a canonical deduplication key to ensure (A, B) and (B, A) are treated identically.
        """
        pair_a = f"{doc_a_id}:{chunk_a_id or ''}"
        pair_b = f"{doc_b_id}:{chunk_b_id or ''}"
        if pair_a > pair_b:
            pair_a, pair_b = pair_b, pair_a
        return f"{pair_a}||{pair_b}||{topic.lower().strip()}"

    def calculate_contradiction_score(
        self,
        semantic_sim: float,
        numeric_conflict: float,
        negation_conflict: float,
        keyword_overlap: float,
        domain_rule: float
    ) -> Tuple[float, str]:
        """
        Calculates weighted contradiction score (0.0 to 1.0) and assigns status:
        >= 0.70 -> CONFIRMED
        0.50 - 0.69 -> POTENTIAL
        < 0.50 -> DISMISSED / NO_CONTRADICTION
        """
        score = (
            (semantic_sim * self.w_semantic) +
            (numeric_conflict * self.w_numeric) +
            (negation_conflict * self.w_negation) +
            (keyword_overlap * self.w_keyword) +
            (domain_rule * self.w_domain)
        )
        if numeric_conflict >= 1.0 or negation_conflict >= 1.0:
            score = max(score, self.potential_threshold)

        score = round(min(1.0, max(0.0, score)), 4)

        if score >= self.contradiction_threshold:
            status = "CONFIRMED"
        elif score >= self.potential_threshold:
            status = "POTENTIAL"
        else:
            status = "DISMISSED"

        return score, status

    def _are_scopes_incompatible(self, scope_a: Optional[str], scope_b: Optional[str]) -> bool:
        """
        Determines whether two scopes differ materially (e.g., 'employees' vs 'contractors').
        """
        if not scope_a or not scope_b:
            return False

        s_a = set(s.strip().lower() for s in scope_a.split(","))
        s_b = set(s.strip().lower() for s in scope_b.split(","))

        if s_a and s_b and s_a.isdisjoint(s_b):
            return True

        return False

    def generate_explanation(
        self,
        doc_a_name: str,
        statement_a: str,
        doc_b_name: str,
        statement_b: str,
        topic: str,
        val_a: Optional[str] = None,
        val_b: Optional[str] = None
    ) -> str:
        """
        Generates human-readable, evidence-first explanation of detected contradiction.
        """
        if val_a and val_b:
            return (
                f"Potential contradiction detected between '{doc_a_name}' and '{doc_b_name}'. "
                f"'{doc_a_name}' specifies '{val_a}' for {topic}, whereas '{doc_b_name}' specifies '{val_b}'. "
                f"Both statements address the same requirement but provide conflicting factual values."
            )
        return (
            f"Potential policy inconsistency detected between '{doc_a_name}' and '{doc_b_name}' regarding '{topic}'. "
            f"Review both statement sources to determine precedence."
        )

    def compare_facts(
        self,
        fact_a: Dict[str, Any],
        fact_b: Dict[str, Any],
        similarity_score: float,
        doc_a: Document,
        doc_b: Document,
        chunk_a: Optional[DocumentChunk] = None,
        chunk_b: Optional[DocumentChunk] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates two candidate facts from different documents for contradictions using weighted score.
        """
        # Scope check
        if self._are_scopes_incompatible(fact_a.get("scope"), fact_b.get("scope")):
            return {
                "status": "DIFFERENT_SCOPE",
                "topic": fact_a.get("topic", "General Scope"),
                "contradiction_type": "OTHER",
                "explanation": f"Statements refer to different scopes or subjects ('{fact_a.get('scope')}' vs '{fact_b.get('scope')}')."
            }

        topic_a = fact_a.get("topic")
        topic_b = fact_b.get("topic")
        
        if topic_a != topic_b and not (("termination" in topic_a.lower() and "termination" in topic_b.lower()) or ("retention" in topic_a.lower() and "retention" in topic_b.lower())):
            return {
                "status": "NO_CONTRADICTION",
                "topic": "Different Topics",
                "contradiction_type": "OTHER",
                "explanation": "Statements address completely different topics."
            }

        topic = topic_a or topic_b or "General Policy"
        val_a = fact_a.get("value")
        val_b = fact_b.get("value")
        unit_a = fact_a.get("unit")
        unit_b = fact_b.get("unit")
        type_a = fact_a.get("fact_type")
        type_b = fact_b.get("fact_type")

        # Calculate component metrics
        numeric_conflict = 1.0 if (val_a and val_b and val_a != val_b) else 0.0
        negation_conflict = 1.0 if (type_a == "BOOLEAN_POLICY" and val_a != val_b) else 0.0
        keyword_overlap = 0.8 if topic_a == topic_b else 0.4
        domain_rule = 1.0 if ("retention" in topic.lower() or "termination" in topic.lower() or "notice" in topic.lower() or "date" in topic.lower() or "payment" in topic.lower()) else 0.5

        contra_score, status_code = self.calculate_contradiction_score(
            similarity_score, numeric_conflict, negation_conflict, keyword_overlap, domain_rule
        )

        # 1. Duration / Retention / Payment / Termination Conflicts
        if type_a in ["DURATION", "TERMINATION_NOTICE", "DATA_RETENTION", "CURE_PERIOD", "AGREEMENT_TERM"] or type_b in ["DURATION", "TERMINATION_NOTICE", "DATA_RETENTION", "CURE_PERIOD", "AGREEMENT_TERM"]:
            if val_a and val_b and val_a != val_b and unit_a == unit_b:
                if "retention" in topic.lower():
                    conflict_type = "RETENTION_CONFLICT"
                elif "termination" in topic.lower() or "notice" in topic.lower():
                    conflict_type = "TERMINATION_CONFLICT"
                elif "payment" in topic.lower() or "net" in topic.lower():
                    conflict_type = "PAYMENT_TERM_CONFLICT"
                else:
                    conflict_type = "DURATION_CONFLICT"

                severity = "HIGH" if "retention" in topic.lower() or "jurisdiction" in topic.lower() else "MEDIUM"
                confidence = round(min(1.0, max(contra_score, similarity_score + 0.15)), 4)
                expl = self.generate_explanation(doc_a.filename, fact_a.get("statement", ""), doc_b.filename, fact_b.get("statement", ""), topic, val_a=f"{val_a} {unit_a}", val_b=f"{val_b} {unit_b}")

                return {
                    "status": "CONTRADICTION" if status_code == "CONFIRMED" else status_code,
                    "topic": topic,
                    "contradiction_type": conflict_type,
                    "statement_a": fact_a.get("statement", ""),
                    "statement_b": fact_b.get("statement", ""),
                    "value_a": val_a,
                    "value_b": val_b,
                    "unit": unit_a,
                    "scope_a": fact_a.get("scope"),
                    "scope_b": fact_b.get("scope"),
                    "severity": severity,
                    "confidence": confidence,
                    "similarity_score": similarity_score,
                    "contradiction_score": contra_score,
                    "explanation": expl
                }

        # 2. Date Conflict
        if type_a == "DATE" or type_b == "DATE":
            if val_a and val_b and val_a != val_b:
                expl = self.generate_explanation(doc_a.filename, fact_a.get("statement", ""), doc_b.filename, fact_b.get("statement", ""), topic, val_a=val_a, val_b=val_b)
                return {
                    "status": "CONTRADICTION" if status_code == "CONFIRMED" else status_code,
                    "topic": topic,
                    "contradiction_type": "DATE_CONFLICT",
                    "statement_a": fact_a.get("statement", ""),
                    "statement_b": fact_b.get("statement", ""),
                    "value_a": val_a,
                    "value_b": val_b,
                    "unit": "date",
                    "scope_a": fact_a.get("scope"),
                    "scope_b": fact_b.get("scope"),
                    "severity": "HIGH",
                    "confidence": round(min(1.0, max(contra_score, similarity_score + 0.10)), 4),
                    "similarity_score": similarity_score,
                    "contradiction_score": contra_score,
                    "explanation": expl
                }

        # 3. Boolean / Policy Requirement Conflict
        if type_a == "BOOLEAN_POLICY" or type_b == "BOOLEAN_POLICY":
            if val_a and val_b and val_a != val_b:
                expl = self.generate_explanation(doc_a.filename, fact_a.get("statement", ""), doc_b.filename, fact_b.get("statement", ""), topic, val_a=val_a, val_b=val_b)
                return {
                    "status": "CONTRADICTION" if status_code == "CONFIRMED" else status_code,
                    "topic": topic,
                    "contradiction_type": "POLICY_REQUIREMENT_CONFLICT",
                    "statement_a": fact_a.get("statement", ""),
                    "statement_b": fact_b.get("statement", ""),
                    "value_a": val_a,
                    "value_b": val_b,
                    "unit": "boolean",
                    "scope_a": fact_a.get("scope"),
                    "scope_b": fact_b.get("scope"),
                    "severity": "HIGH",
                    "confidence": round(min(1.0, max(contra_score, similarity_score + 0.15)), 4),
                    "similarity_score": similarity_score,
                    "contradiction_score": contra_score,
                    "explanation": expl
                }

        return {
            "status": "NO_CONTRADICTION",
            "topic": topic,
            "contradiction_type": "OTHER",
            "explanation": "Statements contain consistent values and facts."
        }

    def generate_candidates(self, chunk: DocumentChunk) -> List[Dict[str, Any]]:
        """
        Retrieves candidate similar chunks from other documents using FAISS semantic search.
        """
        search_results = search_service.search(
            query=chunk.text,
            top_k=50,
            minimum_score=0.20
        )
        return [res for res in search_results if res.get("document_id") != chunk.document_id]

    def find_contradictions(self, db: Session, document_ids: Optional[List[str]] = None) -> List[ContradictionFinding]:
        """
        Executes cross-document contradiction detection across selected or all indexed documents.
        """
        if document_ids is None or len(document_ids) == 0:
            docs = db.query(Document).all()
            document_ids = [d.document_id for d in docs]

        if len(document_ids) < 2:
            logger.info("At least 2 documents are required to detect cross-document contradictions.")
            return []

        # Clear existing findings for target document set
        db.query(ContradictionFinding).filter(
            (ContradictionFinding.document_a_id.in_(document_ids)) | 
            (ContradictionFinding.document_b_id.in_(document_ids))
        ).delete(synchronize_session=False)
        db.commit()

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(document_ids)).all()
        doc_map = {d.document_id: d for d in db.query(Document).filter(Document.document_id.in_(document_ids)).all()}

        processed_canonical_keys = set()
        findings: List[ContradictionFinding] = []

        for chunk_a in chunks:
            doc_a = doc_map.get(chunk_a.document_id)
            if not doc_a:
                continue

            facts_a = fact_extraction_service.extract_facts_from_text(chunk_a.text)
            if not facts_a:
                continue

            candidates = self.generate_candidates(chunk_a)

            for item in candidates:
                chunk_b_id = item.get("chunk_id")
                doc_b_id = item.get("document_id")
                score = item.get("score", 0.0)

                chunk_b = db.query(DocumentChunk).filter(DocumentChunk.chunk_id == chunk_b_id).first()
                if not chunk_b:
                    continue

                doc_b = doc_map.get(doc_b_id) or db.query(Document).filter(Document.document_id == doc_b_id).first()
                if not doc_b:
                    continue

                facts_b = fact_extraction_service.extract_facts_from_text(chunk_b.text)
                if not facts_b:
                    continue

                for f_a in facts_a:
                    for f_b in facts_b:
                        canon_key = self._canonical_key(doc_a.document_id, chunk_a.chunk_id, doc_b.document_id, chunk_b.chunk_id, f_a["topic"])
                        if canon_key in processed_canonical_keys:
                            continue

                        processed_canonical_keys.add(canon_key)

                        eval_res = self.compare_facts(f_a, f_b, score, doc_a, doc_b, chunk_a, chunk_b)
                        if not eval_res or eval_res["status"] not in ["CONTRADICTION", "CONFIRMED", "POTENTIAL"]:
                            continue

                        finding = ContradictionFinding(
                            contradiction_id=str(uuid.uuid4()),
                            document_a_id=doc_a.document_id,
                            document_b_id=doc_b.document_id,
                            chunk_a_id=chunk_a.chunk_id,
                            chunk_b_id=chunk_b.chunk_id,
                            topic=eval_res["topic"],
                            contradiction_type=eval_res["contradiction_type"],
                            status=eval_res["status"] if eval_res["status"] in ["CONFIRMED", "POTENTIAL"] else "CONTRADICTION",
                            statement_a=eval_res["statement_a"],
                            statement_b=eval_res["statement_b"],
                            value_a=eval_res["value_a"],
                            value_b=eval_res["value_b"],
                            unit=eval_res.get("unit"),
                            scope_a=eval_res.get("scope_a"),
                            scope_b=eval_res.get("scope_b"),
                            severity=eval_res.get("severity", "MEDIUM"),
                            confidence=eval_res.get("confidence", 0.85),
                            similarity_score=score,
                            contradiction_score=eval_res.get("contradiction_score", score),
                            explanation=eval_res["explanation"],
                            evidence_a=eval_res["statement_a"],
                            evidence_b=eval_res["statement_b"],
                            page_a=chunk_a.page_number,
                            page_b=chunk_b.page_number,
                            section_a=chunk_a.section,
                            section_b=chunk_b.section,
                            source_a=doc_a.filename,
                            source_b=doc_b.filename,
                            source_filename_a=doc_a.filename,
                            source_filename_b=doc_b.filename
                        )
                        findings.append(finding)

        if findings:
            db.add_all(findings)
            db.commit()

        logger.info(f"Detected {len(findings)} cross-document contradictions across {len(document_ids)} documents.")
        return findings

    def find_document_contradictions(self, db: Session, document_id: str) -> List[ContradictionFinding]:
        """
        Retrieves stored contradiction findings involving a specific document.
        """
        return db.query(ContradictionFinding).filter(
            (ContradictionFinding.document_a_id == document_id) |
            (ContradictionFinding.document_b_id == document_id)
        ).all()

    def find_pairwise_contradictions(self, db: Session, document_a_id: str, document_b_id: str) -> List[ContradictionFinding]:
        """
        Executes pairwise contradiction detection specifically between document A and document B.
        """
        self.find_contradictions(db, [document_a_id, document_b_id])
        return db.query(ContradictionFinding).filter(
            ((ContradictionFinding.document_a_id == document_a_id) & (ContradictionFinding.document_b_id == document_b_id)) |
            ((ContradictionFinding.document_a_id == document_b_id) & (ContradictionFinding.document_b_id == document_a_id))
        ).all()

    def detect_contradictions(self, db: Session, document_ids: Optional[List[str]] = None) -> List[ContradictionFinding]:
        """
        Backward-compatible alias for find_contradictions.
        """
        return self.find_contradictions(db, document_ids)

    def get_document_contradictions(self, db: Session, document_id: str) -> List[ContradictionFinding]:
        """
        Backward-compatible alias for find_document_contradictions.
        """
        return self.find_document_contradictions(db, document_id)

    def get_all_contradictions(self, db: Session) -> List[ContradictionFinding]:
        """
        Retrieves all stored contradiction findings in database.
        """
        return db.query(ContradictionFinding).order_by(ContradictionFinding.created_at.desc()).all()


contradiction_service = ContradictionDetectionService()
ContradictionService = ContradictionDetectionService
