"""
Text Normalization Service.
Cleans whitespace artifacts while strictly preserving dates, numbers, monetary values, section numbers, legal terms, and names.
"""

import re

class TextNormalizationService:
    def normalize_text(self, raw_text: str) -> str:
        """
        Normalizes extracted text:
        - Replaces multiple consecutive blank lines with a double newline
        - Replaces multiple spaces/tabs within a line with a single space
        - Strips leading/trailing line whitespace
        - Preserves all dates, monetary figures ($100,000), section numbers (Section 4.1), and legal terminology.
        """
        if not raw_text:
            return ""

        # Normalize line endings
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Clean line-by-line whitespace without altering punctuation or numbers
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split("\n")]
        
        # Collapse > 2 consecutive empty lines into 2 empty lines
        cleaned_lines = []
        empty_count = 0
        
        for line in lines:
            if not line:
                empty_count += 1
                if empty_count <= 2:
                    cleaned_lines.append("")
            else:
                empty_count = 0
                cleaned_lines.append(line)
                
        return "\n".join(cleaned_lines).strip()

text_normalizer = TextNormalizationService()
