"""
Metadata Extraction Service.
Performs deterministic rule-based extraction for dates, amounts, section numbers, emails, phone numbers, and URLs.
"""

import re
from typing import Dict, List, Any

class MetadataExtractorService:
    PATTERNS = {
        "dates": r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b',
        "monetary_amounts": r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*\s*(?:USD|EUR|GBP)\b',
        "percentages": r'\b\d+(?:\.\d+)?%\b',
        "contract_ids": r'\b(?:AGR|CTR|MSA|NDA|INV|POL)-\d{4}-\d{3,6}\b',
        "email_addresses": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        "phone_numbers": r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "urls": r'https?://[^\s/$.?#].[^\s]*',
        "section_numbers": r'\bSection\s+\d+(?:\.\d+)*\b'
    }

    def extract_metadata(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extracts structured metadata fields from document text with position offsets.
        Returns dict of extracted items grouped by category.
        """
        if not text or not text.strip():
            return {k: [] for k in self.PATTERNS.keys()}

        results = {}
        for category, pattern in self.PATTERNS.items():
            matches = []
            for m in re.finditer(pattern, text, re.IGNORECASE):
                start, end = m.span()
                matched_val = m.group().strip()
                matches.append({
                    "text": matched_val,
                    "start": start,
                    "end": end
                })
            results[category] = matches

        return results

metadata_extractor = MetadataExtractorService()
