"""
Named Entity Recognition (NER) Service using spaCy with Custom Domain Heuristics.
Extracts standard spaCy entities (PERSON, ORG, GPE, DATE, MONEY, LAW, PERCENT)
and custom domain entities (CONTRACT_ID, POLICY_ID, DEADLINE).
"""

import re
from typing import List, Dict, Any, Optional
import spacy
from app.config import settings
from app.core.logging import logger

class NERService:
    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp = None
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy NER model '{model_name}'.")
        except Exception:
            logger.warning(f"spaCy model '{model_name}' not loaded directly. Attempting lazy loading...")
            try:
                import en_core_web_sm
                self.nlp = en_core_web_sm.load()
                logger.info("Loaded spaCy en_core_web_sm model via package import.")
            except Exception as err:
                logger.error(f"Failed to load spaCy model: {err}. NER will run with custom domain rules fallback.")

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts entities from text using spaCy and custom domain regex patterns.
        Returns list of entity dictionaries:
        [{"text": "Acme Corp", "label": "ORG", "start": 10, "end": 19, "context": "..."}]
        """
        if not text or not text.strip():
            return []

        entities = []
        seen_spans = set()

        # 1. spaCy Model Extraction
        if self.nlp:
            try:
                doc = self.nlp(text[:100000])  # Cap text size for fast processing
                for ent in doc.ents:
                    span_key = (ent.start_char, ent.end_char)
                    seen_spans.add(span_key)
                    
                    # Compute surrounding sentence context
                    context = ent.sent.text.strip() if ent.sent else text[max(0, ent.start_char - 40):min(len(text), ent.end_char + 40)]
                    
                    entities.append({
                        "text": ent.text.strip(),
                        "label": ent.label_,
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "context": context
                    })
            except Exception as e:
                logger.error(f"Error executing spaCy NER: {e}")

        # 2. Custom Domain Regex Rules (CONTRACT_ID, POLICY_ID, DEADLINE)
        custom_rules = [
            ("CONTRACT_ID", r'\b(?:AGR|CTR|MSA|NDA|INV|POL)-\d{4}-\d{3,6}\b'),
            ("POLICY_ID", r'\bPOL-\d{4}-[A-Z0-9]+\b'),
            ("DEADLINE", r'\b(?:Net\s+\d+\s+Days|within\s+\d+\s+days|by\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b'),
        ]

        for label, pattern in custom_rules:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                if (start, end) not in seen_spans:
                    seen_spans.add((start, end))
                    matched_text = match.group().strip()
                    context = text[max(0, start - 40):min(len(text), end + 40)].strip()
                    entities.append({
                        "text": matched_text,
                        "label": label,
                        "start": start,
                        "end": end,
                        "context": context
                    })

        # Sort entities by character start position
        entities.sort(key=lambda x: x["start"])
        logger.info(f"Extracted {len(entities)} entities from text snippet.")
        return entities

ner_service = NERService()
