"""
Compliance Rule Engine Service.
Loads compliance rules and evaluates document contents against deterministic and semantic rules.
"""

import json
import re
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings, yaml_config
from app.models.document import Document, DocumentChunk, ComplianceFinding
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

class ComplianceEngine:
    def __init__(self, rules_file: Optional[Path] = None):
        self.rules_file = rules_file or (settings.CONFIG_DIR / "compliance_rules.json")
        self.rules: List[Dict[str, Any]] = []
        
        # Load thresholds from settings.yaml / config
        compliance_config = yaml_config.get("compliance", {})
        self.semantic_threshold = float(compliance_config.get("semantic_match_threshold", 0.55))
        self.strong_threshold = float(compliance_config.get("strong_match_threshold", 0.70))
        self.default_status = compliance_config.get("default_status", "NEEDS_REVIEW")
        
        self.load_rules()

    def load_rules(self, filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Loads and parses compliance rules from JSON configuration file.
        """
        target_file = filepath or self.rules_file
        if not target_file.exists():
            logger.warning(f"Compliance rules file not found at {target_file}")
            self.rules = []
            return self.rules

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            validated_rules = []
            for item in data:
                # Ensure essential fields
                rule_id = item.get("rule_id")
                if not rule_id:
                    continue
                
                rule = {
                    "rule_id": rule_id,
                    "name": item.get("name", f"Rule {rule_id}"),
                    "description": item.get("description", ""),
                    "category": item.get("category", "General Compliance"),
                    "severity": item.get("severity", "MEDIUM").upper(),
                    "enabled": item.get("enabled", True),
                    "requirement": item.get("requirement") or item.get("description", ""),
                    "document_types": item.get("document_types") or item.get("required_for", []),
                    "required_for": item.get("required_for") or item.get("document_types", []),
                    "keywords": item.get("keywords", []),
                    "patterns": item.get("patterns", []),
                    "evaluation": item.get("evaluation", {"type": "presence"}),
                    "remediation": item.get("remediation") or item.get("recommendation", "")
                }
                validated_rules.append(rule)
                
            self.rules = validated_rules
            logger.info(f"Loaded {len(self.rules)} compliance rules from {target_file}")
            return self.rules
            
        except Exception as e:
            logger.error(f"Error loading compliance rules from {target_file}: {e}")
            self.rules = []
            return self.rules

    def get_rules(self) -> List[Dict[str, Any]]:
        """
        Returns all currently loaded rules.
        """
        return self.rules

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Finds a single rule by ID.
        """
        for rule in self.rules:
            if rule["rule_id"].upper() == rule_id.upper():
                return rule
        return None

    def is_rule_applicable(self, rule: Dict[str, Any], doc_type: str, filename: str = "") -> bool:
        """
        Determines whether a rule applies to a specific document type.
        """
        doc_types = rule.get("document_types") or rule.get("required_for", [])
        if not doc_types or "*" in doc_types or "All" in doc_types:
            return True

        normalized_doc_type = (doc_type or "").strip().lower()
        if not normalized_doc_type or normalized_doc_type == "unclassified":
            # If doc type is unclassified, check if filename matches any target type
            filename_lower = filename.lower()
            if any(t.lower() in filename_lower for t in doc_types):
                return True
            # Default unclassified docs to evaluate relevant contract/policy rules
            return True

        for req_type in doc_types:
            req_norm = req_type.strip().lower()
            if req_norm in normalized_doc_type or normalized_doc_type in req_norm:
                return True
            # Check common synonyms
            if req_norm == "contract" and ("agreement" in normalized_doc_type or "contract" in normalized_doc_type):
                return True
            if req_norm == "policy" and ("policy" in normalized_doc_type or "compliance" in normalized_doc_type):
                return True

        return False

    def _evaluate_deterministic(self, rule: Dict[str, Any], text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Runs regex pattern and keyword checks against document text with negative context handling.
        Returns: (found, matched_evidence, matched_explanation)
        """
        norm_text = text.lower()
        negation_terms = ["omit", "omits", "omitted", "deliberately omits", "lacks", "without any", "does not contain", "not included", "missing"]

        def is_negated(start_pos: int) -> bool:
            prefix = norm_text[max(0, start_pos - 60):start_pos]
            return any(neg in prefix for neg in negation_terms)

        # 1. Pattern matching
        patterns = rule.get("patterns", [])
        for pattern_str in patterns:
            try:
                regex = re.compile(pattern_str, re.IGNORECASE)
                for match in regex.finditer(text):
                    if not is_negated(match.start()):
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        snippet = text[start:end].strip().replace("\n", " ")
                        return True, snippet, f"Matched rule pattern '{pattern_str}'"
            except Exception as e:
                logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")

        # 2. Keyword matching
        keywords = rule.get("keywords", [])
        matched_keywords = []
        first_snippet = None
        for kw in keywords:
            kw_lower = kw.lower()
            pos = norm_text.find(kw_lower)
            while pos != -1:
                if not is_negated(pos):
                    matched_keywords.append(kw)
                    if not first_snippet:
                        start = max(0, pos - 100)
                        end = min(len(text), pos + len(kw) + 100)
                        first_snippet = text[start:end].strip().replace("\n", " ")
                    break
                pos = norm_text.find(kw_lower, pos + 1)

        if matched_keywords:
            expl = f"Matched keyword(s): {', '.join(matched_keywords)}"
            return True, first_snippet, expl

        return False, None, "No exact keywords or regex patterns matched in document text."


    def evaluate_rule(self, db: Session, rule: Dict[str, Any], doc: Document) -> Dict[str, Any]:
        """
        Evaluates a single compliance rule against a document using hybrid (deterministic + semantic) evaluation.
        """
        doc_text = doc.normalized_text or doc.extracted_text or ""
        predicted_type = doc.predicted_document_type or "Unclassified"
        
        # Check rule applicability
        if not self.is_rule_applicable(rule, predicted_type, doc.filename):
            return {
                "rule_id": rule["rule_id"],
                "status": "NOT_APPLICABLE",
                "severity": rule["severity"],
                "title": rule["name"],
                "explanation": f"Rule does not apply to document type '{predicted_type}'.",
                "evidence_text": None,
                "chunk_id": None,
                "page_number": None,
                "section": None,
                "relevance_score": 0.0,
                "remediation": rule["remediation"]
            }

        eval_config = rule.get("evaluation", {})
        eval_type = eval_config.get("type", "presence").lower()
        semantic_query = eval_config.get("semantic_query") or f"{rule['name']} {rule['description']}"

        # 1. Deterministic Evaluation
        det_found, det_evidence, det_expl = self._evaluate_deterministic(rule, doc_text)

        # 2. Semantic Vector Search
        search_results = search_service.search(
            query=semantic_query,
            top_k=3,
            document_id=doc.document_id
        )

        top_result = search_results[0] if search_results else None
        sem_score = top_result["score"] if top_result else 0.0
        sem_text = top_result["text"] if top_result else None
        sem_chunk_id = top_result.get("chunk_id") if top_result else None
        sem_page = top_result.get("page_number") if top_result else None
        sem_section = top_result.get("section") if top_result else None

        # 3. Rule Type Specific Logic
        status = "NEEDS_REVIEW"
        explanation = ""
        evidence_text = det_evidence or sem_text
        relevance_score = sem_score
        chunk_id = sem_chunk_id
        page_number = sem_page
        section = sem_section

        if eval_type == "absence":
            if det_found or sem_score >= self.strong_threshold:
                status = "FAIL"
                explanation = f"Prohibited clause or term detected in document ({det_expl})."
            else:
                status = "PASS"
                explanation = "Prohibited clause or term was not found in the document."

        elif eval_type == "pattern":
            if det_found:
                status = "PASS"
                explanation = f"Required pattern satisfied: {det_expl}."
            else:
                status = "FAIL"
                explanation = f"Required pattern not identified in document for {rule['name']}."

        elif eval_type == "keyword":
            if det_found:
                status = "PASS"
                explanation = f"Required compliance keyword(s) identified: {det_expl}."
            elif sem_score >= self.semantic_threshold:
                status = "NEEDS_REVIEW"
                explanation = "Keywords not explicitly found, but related semantic concepts were identified."
            else:
                status = "FAIL"
                explanation = f"Document is missing required keywords for {rule['name']}."

        elif eval_type == "threshold":
            max_val = eval_config.get("max_value")
            # Extract numbers near retention keywords
            ret_match = re.search(r"(?:retain|retention|stored?)\s+(?:for\s+)?(\d+)\s+years?", doc_text, re.IGNORECASE)
            if ret_match and max_val is not None:
                val = int(ret_match.group(1))
                if val <= max_val:
                    status = "PASS"
                    explanation = f"Data retention period of {val} years satisfies the maximum requirement of {max_val} years."
                else:
                    status = "FAIL"
                    explanation = f"Data retention period of {val} years exceeds maximum allowed {max_val} years."
                evidence_text = ret_match.group(0)
            elif det_found or sem_score >= self.semantic_threshold:
                status = "PASS" if sem_score >= self.strong_threshold else "NEEDS_REVIEW"
                explanation = f"Retention policy mentioned in document. Relevance score: {round(sem_score, 4)}."
            else:
                status = "FAIL"
                explanation = "No explicit data retention policy threshold identified."

        else:  # 'presence' or 'semantic' or default
            if det_found and sem_score >= self.strong_threshold:
                status = "PASS"
                explanation = f"Strong compliance evidence identified ({det_expl}) with high semantic match ({round(sem_score, 4)})."
            elif det_found:
                status = "PASS"
                explanation = f"Compliance clause verified via keyword/pattern match ({det_expl})."
            elif sem_score >= self.strong_threshold:
                status = "PASS"
                explanation = f"Compliance clause verified via strong semantic retrieval (Score: {round(sem_score, 4)})."
            elif sem_score >= self.semantic_threshold:
                status = "NEEDS_REVIEW"
                explanation = f"Moderate evidence found for {rule['name']} (Semantic score: {round(sem_score, 4)}). Manual verification recommended."
            else:
                status = "FAIL"
                explanation = f"Document does not contain sufficient evidence of {rule['name']}."

        return {
            "rule_id": rule["rule_id"],
            "status": status,
            "severity": rule["severity"],
            "title": rule["name"],
            "explanation": explanation,
            "evidence_text": evidence_text,
            "chunk_id": chunk_id,
            "page_number": page_number,
            "section": section,
            "relevance_score": relevance_score,
            "remediation": rule["remediation"] if status != "PASS" else None
        }

    def evaluate_document(self, db: Session, document_id: str) -> List[ComplianceFinding]:
        """
        Evaluates all enabled rules against a document and persists ComplianceFinding records in database.
        """
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        # Delete existing findings for this document
        db.query(ComplianceFinding).filter(ComplianceFinding.document_id == document_id).delete()
        db.commit()

        findings: List[ComplianceFinding] = []
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
                
            res = self.evaluate_rule(db, rule, doc)
            finding = ComplianceFinding(
                finding_id=str(uuid.uuid4()),
                document_id=doc.document_id,
                rule_id=res["rule_id"],
                status=res["status"],
                severity=res["severity"],
                title=res["title"],
                explanation=res["explanation"],
                evidence_text=res["evidence_text"],
                chunk_id=res["chunk_id"],
                page_number=res["page_number"],
                section=res["section"],
                source_filename=doc.filename,
                relevance_score=res["relevance_score"],
                remediation=res["remediation"]
            )
            findings.append(finding)

        db.add_all(findings)
        db.commit()

        return db.query(ComplianceFinding).filter(ComplianceFinding.document_id == document_id).all()

    def evaluate_documents(self, db: Session, document_ids: List[str]) -> Dict[str, List[ComplianceFinding]]:
        """
        Evaluates compliance rules for multiple documents.
        """
        results = {}
        for doc_id in document_ids:
            try:
                results[doc_id] = self.evaluate_document(db, doc_id)
            except Exception as e:
                logger.error(f"Failed to audit document {doc_id}: {e}")
                results[doc_id] = []
        return results


compliance_engine = ComplianceEngine()
