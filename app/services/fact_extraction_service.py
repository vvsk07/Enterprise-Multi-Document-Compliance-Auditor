"""
Fact Extraction Service for Cross-Document Contradiction Detection.
Extracts structured facts (durations, dates, monetary amounts, boolean policy requirements, and subjects/scopes) from text chunks.
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twelve": 12, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90
}

class FactExtractionService:
    def extract_facts_from_text(self, text: str, chunk_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extracts structured fact items from text snippet.
        """
        facts = []
        if not text or not text.strip():
            return facts

        # 1. Scope Detection
        scope = self.extract_scope(text)

        # 2. Extract Duration / Notice Period Facts
        duration_facts = self._extract_durations(text, scope)
        facts.extend(duration_facts)

        # 3. Extract Date Facts
        date_facts = self._extract_dates(text, scope)
        facts.extend(date_facts)

        # 4. Extract Monetary / Percentage Facts
        amount_facts = self._extract_amounts(text, scope)
        facts.extend(amount_facts)

        # 5. Extract Boolean / Policy Requirement Facts
        policy_facts = self._extract_policy_requirements(text, scope)
        facts.extend(policy_facts)

        return facts

    def extract_scope(self, text: str) -> Optional[str]:
        """
        Extracts subject/scope context from text using word boundaries.
        """
        norm = text.lower()
        found_scopes = []
        
        if re.search(r"\bcontractors?\b", norm):
            found_scopes.append("contractors")
        if re.search(r"\b(employees?|staff)\b", norm):
            found_scopes.append("employees")
        if re.search(r"\bvendors?\b", norm):
            found_scopes.append("vendors")
        if re.search(r"\bcustomers?\b", norm):
            found_scopes.append("customers")
        if re.search(r"\bindia\b", norm):
            found_scopes.append("india")
        if re.search(r"\b(us|usa|united states)\b", norm):
            found_scopes.append("us")

        return ", ".join(found_scopes) if found_scopes else None

    def _extract_durations(self, text: str, scope: Optional[str]) -> List[Dict[str, Any]]:
        facts = []
        norm = text.lower()

        # Regex pattern matching both numeric digits and word numbers with optional parentheses: e.g. "30 days", "(30) days", "thirty (30) days", "2 years"
        pattern = r"\b(?:(?P<word>thirty|sixty|ninety|twenty|ten|five|two|one|twelve)|(?P<digits>\d+))\b[\s\)]*(?P<unit>days?|months?|years?|weeks?)\b"
        
        matches = re.finditer(pattern, norm)
        seen_spans = set()

        for m in matches:
            span = (m.start(), m.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)

            if m.group("digits"):
                val = int(m.group("digits"))
            elif m.group("word"):
                val = WORD_NUMBERS.get(m.group("word"), 0)
            else:
                continue

            raw_unit = m.group("unit").rstrip('s')
            unit = "days" if raw_unit in ["day", "days"] else ("months" if raw_unit in ["month", "months"] else ("years" if raw_unit in ["year", "years"] else raw_unit))

            start_pos = m.start()
            sentence_window = norm[max(0, start_pos - 80):min(len(norm), start_pos + 80)]

            # Topic inference
            topic = "General Duration"
            fact_type = "DURATION"

            if any(k in sentence_window for k in ["terminate", "termination", "notice"]):
                topic = "Termination Notice Period"
                fact_type = "TERMINATION_NOTICE"
            elif any(k in sentence_window for k in ["retain", "retention", "archive", "store", "delete", "deletion"]):
                topic = "Data Retention Period"
                fact_type = "DATA_RETENTION"

            elif any(k in sentence_window for k in ["cure", "remedy", "breach"]):
                topic = "Cure Period"
                fact_type = "CURE_PERIOD"
            elif any(k in sentence_window for k in ["term", "duration", "validity"]):
                topic = "Agreement Term"
                fact_type = "AGREEMENT_TERM"

            original_snippet = text[max(0, start_pos - 60):min(len(text), m.end() + 60)].strip().replace("\n", " ")

            facts.append({
                "fact_type": fact_type,
                "topic": topic,
                "value": str(val),
                "numeric_value": val,
                "unit": unit,
                "raw_text": m.group(0),
                "statement": original_snippet,
                "scope": scope
            })

        return facts

    def _extract_dates(self, text: str, scope: Optional[str]) -> List[Dict[str, Any]]:
        facts = []
        norm = text.lower()

        # Regex for dates: January 15, 2029 / 15 January 2029 / 2029-01-15
        date_pattern = r"\b(?:(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4})|(?:\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{4})|(?:\d{4}-\d{2}-\d{2})\b"
        
        matches = re.finditer(date_pattern, norm)
        for m in matches:
            date_str = text[m.start():m.end()]
            start_pos = m.start()
            sentence_window = norm[max(0, start_pos - 80):min(len(norm), m.end() + 80)]

            topic = "General Date"
            if any(k in sentence_window for k in ["effective", "dated as of", "execution"]):
                topic = "Effective Date"
            elif any(k in sentence_window for k in ["expire", "expiration", "expires", "end date"]):
                topic = "Expiration Date"
            elif any(k in sentence_window for k in ["due date", "payment due"]):
                topic = "Payment Due Date"

            original_snippet = text[max(0, start_pos - 60):min(len(text), m.end() + 60)].strip().replace("\n", " ")

            facts.append({
                "fact_type": "DATE",
                "topic": topic,
                "value": date_str,
                "numeric_value": None,
                "unit": "date",
                "raw_text": date_str,
                "statement": original_snippet,
                "scope": scope
            })

        return facts

    def _extract_amounts(self, text: str, scope: Optional[str]) -> List[Dict[str, Any]]:
        facts = []
        norm = text.lower()

        money_pattern = r"(\$|₹|USD|EUR)\s*([\d,]+(?:\.\d+)?)"
        pct_pattern = r"\b(\d+(?:\.\d+)?)\s*(%|percent)\b"

        for m in re.finditer(money_pattern, text):
            curr = m.group(1)
            val_str = m.group(2).replace(",", "")
            try:
                val_num = float(val_str)
                start_pos = m.start()
                sentence_window = norm[max(0, start_pos - 60):min(len(norm), m.end() + 60)]
                
                topic = "Monetary Amount"
                if "rate" in sentence_window or "hourly" in sentence_window:
                    topic = "Hourly Rate"
                elif "penalty" in sentence_window or "fine" in sentence_window:
                    topic = "Penalty Fee"
                elif "fee" in sentence_window or "payment" in sentence_window:
                    topic = "Payment Fee"

                facts.append({
                    "fact_type": "MONEY",
                    "topic": topic,
                    "value": f"{curr}{val_str}",
                    "numeric_value": val_num,
                    "unit": curr,
                    "raw_text": m.group(0),
                    "statement": text[max(0, start_pos - 60):min(len(text), m.end() + 60)].strip().replace("\n", " "),
                    "scope": scope
                })
            except ValueError:
                pass

        for m in re.finditer(pct_pattern, norm):
            val_str = m.group(1)
            try:
                val_num = float(val_str)
                start_pos = m.start()
                facts.append({
                    "fact_type": "PERCENTAGE",
                    "topic": "Percentage Rate",
                    "value": f"{val_str}%",
                    "numeric_value": val_num,
                    "unit": "%",
                    "raw_text": m.group(0),
                    "statement": text[max(0, start_pos - 60):min(len(text), m.end() + 60)].strip().replace("\n", " "),
                    "scope": scope
                })
            except ValueError:
                pass

        return facts

    def _extract_policy_requirements(self, text: str, scope: Optional[str]) -> List[Dict[str, Any]]:
        facts = []
        norm = text.lower()

        permitted_kw = ["is permitted", "are permitted", "may share", "is allowed", "are allowed", "authorized"]
        prohibited_kw = ["is prohibited", "are prohibited", "forbidden", "not permitted", "must not", "not allowed", "strictly prohibited"]

        is_permitted = any(kw in norm for kw in permitted_kw)
        is_prohibited = any(kw in norm for kw in prohibited_kw)

        if is_permitted or is_prohibited:
            topic = "Policy Requirement"
            if "sharing" in norm or "external" in norm or "third party" in norm or "disclosure" in norm:
                topic = "External Data Sharing Policy"
            elif "remote" in norm or "work from home" in norm:
                topic = "Remote Work Policy"

            state_val = "PROHIBITED" if is_prohibited else "PERMITTED"
            facts.append({
                "fact_type": "BOOLEAN_POLICY",
                "topic": topic,
                "value": state_val,
                "numeric_value": None,
                "unit": "boolean",
                "raw_text": state_val,
                "statement": text.strip().replace("\n", " "),
                "scope": scope
            })

        return facts

fact_extraction_service = FactExtractionService()
