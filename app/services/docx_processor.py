"""
DOCX Processing Service using python-docx with Section & Table Extraction.
"""

from typing import List, Dict, Any, Tuple
import docx
from app.core.logging import logger

class DOCXProcessor:
    def process_docx(self, file_path: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Processes a DOCX file preserving section headings and tables.
        Returns: (sections_data, combined_text)
        where sections_data is list of dicts:
        [{"section": "Confidentiality", "text": "..."}]
        """
        sections = []
        combined_text_parts = []
        current_section = "General"
        current_text_buf = []
        
        try:
            doc = docx.Document(file_path)
            
            for elem in doc.element.body:
                # Paragraph processing
                if elem.tag.endswith('p'):
                    p = docx.text.paragraph.Paragraph(elem, doc)
                    text = p.text.strip()
                    if not text:
                        continue
                    
                    # Check if paragraph is a heading
                    if p.style and p.style.name and 'Heading' in p.style.name:
                        if current_text_buf:
                            section_text = "\n".join(current_text_buf)
                            sections.append({"section": current_section, "text": section_text})
                            combined_text_parts.append(f"--- Section: {current_section} ---\n{section_text}")
                            current_text_buf = []
                        current_section = text
                    else:
                        current_text_buf.append(text)
                        
                # Table processing
                elif elem.tag.endswith('tbl'):
                    table = docx.table.Table(elem, doc)
                    table_rows = []
                    for row in table.rows:
                        row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_data:
                            table_rows.append(" | ".join(row_data))
                    if table_rows:
                        table_text = "[TABLE]\n" + "\n".join(table_rows) + "\n[/TABLE]"
                        current_text_buf.append(table_text)

            # Flush remaining buffer
            if current_text_buf:
                section_text = "\n".join(current_text_buf)
                sections.append({"section": current_section, "text": section_text})
                combined_text_parts.append(f"--- Section: {current_section} ---\n{section_text}")

            full_text = "\n\n".join(combined_text_parts) if combined_text_parts else ""
            return sections, full_text

        except Exception as e:
            logger.error(f"Failed to process DOCX file {file_path}: {e}")
            raise RuntimeError(f"DOCX extraction error: {str(e)}")

docx_processor = DOCXProcessor()
