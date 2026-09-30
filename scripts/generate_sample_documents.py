"""
Script to programmatically generate sample DOCX and PDF test documents.
"""

from pathlib import Path
import docx
import fitz  # PyMuPDF

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def generate_sample_docx():
    doc_path = SAMPLE_DIR / "sample_contract.docx"
    doc = docx.Document()
    doc.add_heading("NON-DISCLOSURE AGREEMENT", 0)
    
    p1 = doc.add_paragraph("This Non-Disclosure Agreement ('NDA') is effective as of January 10, 2026.")
    doc.add_heading("1. Confidential Information", level=1)
    p2 = doc.add_paragraph("Confidential Information includes technical specs, customer lists, and financial reports.")
    
    doc.add_heading("2. Termination", level=1)
    p3 = doc.add_paragraph("Either party may terminate this NDA with 30 days written notice.")
    
    table = doc.add_table(rows=2, cols=2)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Party Name"
    hdr_cells[1].text = "Jurisdiction"
    
    row_cells = table.rows[1].cells
    row_cells[0].text = "Acme Corp"
    row_cells[1].text = "Delaware, USA"
    
    doc.save(str(doc_path))
    print(f"[+] Generated DOCX: {doc_path.resolve()}")

def generate_sample_pdf():
    pdf_path = SAMPLE_DIR / "sample_policy.pdf"
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), "COMPANY PRIVACY POLICY", fontsize=18)
    page1.insert_text((50, 100), "Section 1: Data Protection Principles", fontsize=14)
    page1.insert_text((50, 130), "We comply with GDPR regulations. All personal data is processed lawfully and transparently.", fontsize=11)
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Section 2: Governing Law", fontsize=14)
    page2.insert_text((50, 80), "This policy is governed by the laws of California. Disputes shall be resolved in San Francisco courts.", fontsize=11)
    
    doc.save(str(pdf_path))
    doc.close()
    print(f"[+] Generated PDF: {pdf_path.resolve()}")

if __name__ == "__main__":
    generate_sample_docx()
    generate_sample_pdf()
