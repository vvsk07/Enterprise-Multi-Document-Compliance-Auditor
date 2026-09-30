"""
PDF Processing Service using PyMuPDF (fitz) with Scanned PDF Detection & OCR Fallback.
"""

from typing import List, Dict, Any, Tuple
import pymupdf
from app.services.ocr_service import ocr_service
from app.core.logging import logger

class PDFProcessor:
    def __init__(self, min_text_chars_per_page: int = 30):
        self.min_text_chars_per_page = min_text_chars_per_page

    def process_pdf(self, file_path: str) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Processes a PDF file page by page.
        Returns: (pages_data, document_ocr_required, total_page_count)
        where pages_data is list of dicts:
        {"page_number": 1, "text": "...", "ocr_applied": False, "ocr_required": False}
        """
        pages_data = []
        doc_ocr_required = False
        
        try:
            doc = pymupdf.open(file_path)
            total_pages = len(doc)
            
            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_number = page_idx + 1
                raw_text = page.get_text("text").strip()
                
                page_ocr_required = len(raw_text) < self.min_text_chars_per_page
                ocr_applied = False
                final_text = raw_text
                
                if page_ocr_required:
                    doc_ocr_required = True
                    logger.info(f"PDF Page {page_number} has low selectable text length ({len(raw_text)} chars). Triggering OCR check...")
                    
                    # Try rendering page as PNG image for OCR
                    try:
                        pix = page.get_pixmap(dpi=150)
                        image_bytes = pix.tobytes("png")
                        ocr_text, success, status_msg = ocr_service.perform_ocr_on_image_bytes(image_bytes)
                        
                        if success and len(ocr_text) > 0:
                            final_text = ocr_text
                            ocr_applied = True
                            logger.info(f"OCR successfully extracted {len(ocr_text)} characters from page {page_number}.")
                        else:
                            logger.warning(f"OCR not applied for page {page_number}: {status_msg}")
                    except Exception as ocr_err:
                        logger.error(f"Error rendering PDF page {page_number} for OCR: {ocr_err}")

                pages_data.append({
                    "page_number": page_number,
                    "text": final_text,
                    "ocr_applied": ocr_applied,
                    "ocr_required": page_ocr_required
                })
                
            doc.close()
            return pages_data, doc_ocr_required, total_pages
            
        except Exception as e:
            logger.error(f"Failed to process PDF file {file_path}: {e}")
            raise RuntimeError(f"PDF extraction error: {str(e)}")

pdf_processor = PDFProcessor()
