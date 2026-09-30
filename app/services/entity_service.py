"""
Entity Normalization Service.
Normalizes entity text representations (e.g. company suffixes, dates, whitespace, case formatting).
"""

import re

class EntityNormalizationService:
    CORPORATE_SUFFIXES = [
        r'\bInc\.?\b', r'\bLLC\b', r'\bCorp\.?\b', r'\bCorporation\b',
        r'\bLtd\.?\b', r'\bLimited\b', r'\bPvt\.?\b', r'\bPrivate\b',
        r'\bSystems\b', r'\bTechnologies\b', r'\bSolutions\b', r'\bGroup\b'
    ]

    def normalize_entity_text(self, text: str, label: str) -> str:
        """
        Normalizes an entity text based on its label.
        Returns canonical normalized string.
        """
        if not text or not text.strip():
            return ""

        cleaned = text.strip()

        # Whitespace normalization
        cleaned = re.sub(r'\s+', ' ', cleaned)

        if label in ["ORG", "ORGANIZATION"]:
            # Strip corporate suffixes for canonical match
            norm = cleaned
            for suffix in self.CORPORATE_SUFFIXES:
                norm = re.sub(suffix, '', norm, flags=re.IGNORECASE)
            norm = re.sub(r'[^a-zA-Z0-9\s]', '', norm).strip()
            return norm.title() if norm else cleaned.title()

        elif label in ["PERSON"]:
            # Title case person names and strip titles (Mr., Ms., Dr.)
            norm = re.sub(r'\b(Mr|Ms|Mrs|Dr|Prof)\.\s*', '', cleaned, flags=re.IGNORECASE)
            return norm.strip().title()

        elif label in ["DATE"]:
            # Basic date string cleanup
            return cleaned.strip()

        elif label in ["MONEY"]:
            # Normalize currency representations ($15,000 -> 15000 USD)
            cleaned_val = re.sub(r'[^0-9.]', '', cleaned)
            if cleaned_val:
                return f"${cleaned_val}"
            return cleaned

        return cleaned

entity_normalizer = EntityNormalizationService()
