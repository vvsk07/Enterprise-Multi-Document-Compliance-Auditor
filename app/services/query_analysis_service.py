"""
Query Analysis & Intent Service.
Provides deterministic query parsing without external LLM APIs to detect question types,
intents, requested entities, dates, numerical constraints, and compliance/contradiction domain terms.
"""

import re
from typing import Dict, Any, List, Optional

class QueryAnalysisService:
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyzes a natural language user query and extracts structured metadata to aid retrieval.
        """
        if not query or not query.strip():
            return {
                "raw_query": "",
                "question_type": "empty",
                "intent": "none",
                "document_scope": "All",
                "entity": None,
                "dates": [],
                "numerical_constraints": [],
                "compliance_terms": [],
                "contradiction_terms": []
            }

        q_lower = query.lower().strip()

        # 1. Document Scope detection
        document_scope = "All"
        if any(kw in q_lower for kw in ["contract", "agreement", "msa"]):
            document_scope = "Contract"
        elif any(kw in q_lower for kw in ["nda", "confidentiality agreement"]):
            document_scope = "NDA"
        elif any(kw in q_lower for kw in ["policy", "procedure", "guideline"]):
            document_scope = "Policy"
        elif any(kw in q_lower for kw in ["invoice", "billing", "payment"]):
            document_scope = "Invoice"

        # 2. Compliance Terms detection
        compliance_keywords = [
            "termination", "notice", "confidentiality", "indemnification",
            "retention", "governing law", "jurisdiction", "liability",
            "penalty", "gdpr", "hipaa", "audit", "compliance", "sla"
        ]
        found_compliance = [kw for kw in compliance_keywords if kw in q_lower]

        # 3. Contradiction Terms detection
        contradiction_keywords = [
            "contradiction", "conflict", "mismatch", "inconsistent",
            "differ", "discrepancy", "opposite", "versus", "vs"
        ]
        found_contradiction = [kw for kw in contradiction_keywords if kw in q_lower]

        # 4. Numerical constraints & dates detection
        dates = re.findall(
            r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b',
            q_lower
        )
        numerics = re.findall(r'\b\d+(?:\.\d+)?\s*(?:days?|years?|months?|percent|%|\$|usd|eur|net)\b', q_lower)

        # 5. Question Type & Intent Determination
        question_type = "general_query"
        intent = "information_retrieval"

        if found_contradiction:
            question_type = "contradiction_check"
            intent = "detect_discrepancy"
        elif found_compliance:
            question_type = "compliance_lookup"
            intent = "policy_verification"
        elif any(kw in q_lower for kw in ["what is", "what are", "who is", "where is"]):
            question_type = "fact_lookup"
            intent = "entity_definition"
        elif any(kw in q_lower for kw in ["how long", "how many", "when"]):
            question_type = "quantitative_lookup"
            intent = "constraint_check"

        # 6. Entity extraction heuristic
        entity = None
        vendor_match = re.search(r'\b(vendor|supplier|company [a-z]|client|customer|contractor)\b', q_lower)
        if vendor_match:
            entity = vendor_match.group(1).title()

        return {
            "raw_query": query,
            "question_type": question_type,
            "intent": intent,
            "document_scope": document_scope,
            "entity": entity,
            "dates": dates,
            "numerical_constraints": numerics,
            "compliance_terms": found_compliance,
            "contradiction_terms": found_contradiction
        }

query_analysis_service = QueryAnalysisService()
