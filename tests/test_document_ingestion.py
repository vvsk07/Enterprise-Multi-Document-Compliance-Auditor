"""
Comprehensive Pytest Test Suite for Phase 2 Document Ingestion, Processing, and API Security.
"""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import sanitize_filename, validate_file
from app.services.pdf_processor import pdf_processor
from app.services.docx_processor import docx_processor
from app.services.txt_processor import txt_processor
from app.services.chunking_service import chunking_service
from app.services.ocr_service import ocr_service
from app.models.document import Document, DocumentChunk

# Configure test database in memory with StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_sanitize_filename_path_traversal():
    unsafe_name = "../../etc/passwd.txt"
    safe = sanitize_filename(unsafe_name)
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe
    assert safe.endswith(".txt")


def test_validate_file():
    # Empty file
    valid, msg = validate_file("test.pdf", 0)
    assert not valid
    assert "empty" in msg.lower()

    # Oversized file
    valid, msg = validate_file("test.pdf", 50 * 1024 * 1024)
    assert not valid
    assert "exceeds" in msg.lower()

    # Unsupported extension
    valid, msg = validate_file("test.exe", 1024)
    assert not valid
    assert "unsupported" in msg.lower()

    # Valid file
    valid, msg = validate_file("test.docx", 1024)
    assert valid
    assert msg == ""


def test_txt_extraction():
    txt_path = SAMPLE_DIR / "compliant_contract.txt"
    assert txt_path.exists()
    text = txt_processor.process_txt(str(txt_path))
    assert "MASTER SERVICES AGREEMENT" in text
    assert "Section 1. Term of Agreement" in text


def test_docx_extraction():
    docx_path = SAMPLE_DIR / "sample_contract.docx"
    assert docx_path.exists()
    sections, text = docx_processor.process_docx(str(docx_path))
    assert len(sections) >= 2
    assert any("Confidential Information" in s["section"] for s in sections)
    assert "Acme Corp" in text


def test_pdf_extraction():
    pdf_path = SAMPLE_DIR / "sample_policy.pdf"
    assert pdf_path.exists()
    pages, ocr_req, total_pages = pdf_processor.process_pdf(str(pdf_path))
    assert total_pages == 2
    assert pages[0]["page_number"] == 1
    assert "COMPANY PRIVACY POLICY" in pages[0]["text"]


def test_chunking_service():
    sample_text = (
        "Section 1. Confidentiality Obligations. "
        "The receiving party shall not disclose Confidential Information to any third party without consent. "
        "This obligation shall survive termination of the agreement for five years. "
        "Section 2. Governing Law. This agreement shall be governed by Delaware law."
    )
    chunks = chunking_service.chunk_text(
        text=sample_text,
        document_id="test-doc-123",
        filename="test.txt",
        page_number=1,
        section="Confidentiality"
    )
    assert len(chunks) > 0
    assert chunks[0]["document_id"] == "test-doc-123"
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["section"] == "Confidentiality"
    assert "Confidentiality Obligations" in chunks[0]["text"]


def test_ocr_unavailable_graceful_fallback():
    # Verify that OCR service does not crash if unavailable
    is_avail = ocr_service.is_ocr_available()
    text, success, status = ocr_service.perform_ocr_on_image_bytes(b"dummy_bytes")
    if not is_avail:
        assert not success
        assert "UNAVAILABLE" in status
    else:
        assert isinstance(text, str)


def test_api_upload_and_ingestion():
    txt_path = SAMPLE_DIR / "compliant_contract.txt"
    with open(txt_path, "rb") as f:
        content = f.read()
    response = client.post(
        "/documents/upload",
        files=[("files", ("compliant_contract.txt", content, "text/plain"))]
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["uploaded_files"]) == 1, f"Failed files: {data.get('failed_files')}"
    doc_info = data["uploaded_files"][0]
    assert doc_info["filename"] == "compliant_contract.txt"
    assert doc_info["document_status"] == "PROCESSED"
    assert doc_info["chunks_count"] > 0
    doc_id = doc_info["document_id"]

    # Test GET /documents
    list_res = client.get("/documents")
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["document_id"] == doc_id for d in docs)

    # Test GET /documents/{id}
    detail_res = client.get(f"/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "MASTER SERVICES AGREEMENT" in detail["extracted_text"]
    assert len(detail["chunks"]) > 0

    # Test POST /documents/{id}/process
    reprocess_res = client.post(f"/documents/{doc_id}/process")
    assert reprocess_res.status_code == 200
    assert reprocess_res.json()["status"] == "PROCESSED"


def test_api_upload_invalid_file():
    # Test uploading empty file
    response = client.post(
        "/documents/upload",
        files=[("files", ("empty.txt", b"", "text/plain"))]
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["failed_files"]) == 1
    assert "empty" in data["failed_files"][0]["error"].lower()
