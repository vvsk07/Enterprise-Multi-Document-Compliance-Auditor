"""
Comprehensive Pytest Test Suite for Phase 6:
Cross-Document Contradiction Detection Engine, Scoring, Evidentiary Traceability, and API Endpoints.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.services.fact_extraction_service import fact_extraction_service
from app.services.contradiction_service import contradiction_service
from app.services.contradiction_report_service import contradiction_report_service
from app.models.document import Document, DocumentChunk, ContradictionFinding, CrossDocumentContradiction

# Configure in-memory database with StaticPool for thread-safe test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def reset_db_override():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield

client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_1_detect_30_vs_60_days_vendor_notice():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-v30", filename="policy_vendor_30_days.txt", safe_filename="policy_vendor_30_days.txt", file_path="/tmp/v30", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-v60", filename="policy_vendor_60_days.txt", safe_filename="policy_vendor_60_days.txt", file_path="/tmp/v60", file_type="txt", file_size=100)
    db.add_all([doc_a, doc_b])

    chunk_a = DocumentChunk(chunk_id="cv30", document_id="doc-v30", chunk_index=0, page_number=1, section="Notice", text="All vendors must provide at least 30 days advance written notice before terminating an active operational contract.")
    chunk_b = DocumentChunk(chunk_id="cv60", document_id="doc-v60", chunk_index=0, page_number=1, section="Notice", text="All vendors must provide at least 60 days advance written notice before terminating an active operational contract.")
    db.add_all([chunk_a, chunk_b])
    db.commit()

    facts_a = fact_extraction_service.extract_facts_from_text(chunk_a.text)
    facts_b = fact_extraction_service.extract_facts_from_text(chunk_b.text)

    res = contradiction_service.compare_facts(facts_a[0], facts_b[0], similarity_score=0.95, doc_a=doc_a, doc_b=doc_b, chunk_a=chunk_a, chunk_b=chunk_b)
    assert res["status"] in ["CONTRADICTION", "CONFIRMED"]
    assert res["contradiction_type"] in ["TERMINATION_CONFLICT", "DURATION_CONFLICT"]
    assert res["value_a"] == "30"
    assert res["value_b"] == "60"
    db.close()


def test_2_detect_7_years_vs_3_years_retention():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-ret7", filename="data_retention_7_years.txt", safe_filename="data_retention_7_years.txt", file_path="/tmp/r7", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-ret3", filename="data_retention_3_years.txt", safe_filename="data_retention_3_years.txt", file_path="/tmp/r3", file_type="txt", file_size=100)
    db.add_all([doc_a, doc_b])

    chunk_a = DocumentChunk(chunk_id="cret7", document_id="doc-ret7", chunk_index=0, page_number=1, section="Retention", text="Employees must retain all financial transactions and compliance records for seven (7) years from creation date.")
    chunk_b = DocumentChunk(chunk_id="cret3", document_id="doc-ret3", chunk_index=0, page_number=1, section="Retention", text="Employees must delete all financial transactions and compliance records after three (3) years from creation date.")
    db.add_all([chunk_a, chunk_b])
    db.commit()

    facts_a = fact_extraction_service.extract_facts_from_text(chunk_a.text)
    facts_b = fact_extraction_service.extract_facts_from_text(chunk_b.text)

    res = contradiction_service.compare_facts(facts_a[0], facts_b[0], similarity_score=0.92, doc_a=doc_a, doc_b=doc_b, chunk_a=chunk_a, chunk_b=chunk_b)
    assert res["status"] in ["CONTRADICTION", "CONFIRMED"]
    assert res["contradiction_type"] in ["RETENTION_CONFLICT", "DURATION_CONFLICT"]
    assert res["value_a"] == "7"
    assert res["value_b"] == "3"
    db.close()


def test_3_detect_net_30_vs_net_60_payment_terms():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-p30", filename="payment_net30.txt", safe_filename="payment_net30.txt", file_path="/tmp/p30", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-p60", filename="payment_net60.txt", safe_filename="payment_net60.txt", file_path="/tmp/p60", file_type="txt", file_size=100)
    db.add_all([doc_a, doc_b])

    chunk_a = DocumentChunk(chunk_id="cp30", document_id="doc-p30", chunk_index=0, page_number=1, section="Payment", text="Payment terms for all submitted vendor invoices are Net 30 days from invoice receipt date.")
    chunk_b = DocumentChunk(chunk_id="cp60", document_id="doc-p60", chunk_index=0, page_number=1, section="Payment", text="Payment terms for all submitted vendor invoices are Net 60 days from invoice receipt date.")
    db.add_all([chunk_a, chunk_b])
    db.commit()

    facts_a = fact_extraction_service.extract_facts_from_text(chunk_a.text)
    facts_b = fact_extraction_service.extract_facts_from_text(chunk_b.text)

    res = contradiction_service.compare_facts(facts_a[0], facts_b[0], similarity_score=0.94, doc_a=doc_a, doc_b=doc_b, chunk_a=chunk_a, chunk_b=chunk_b)
    assert res["status"] in ["CONTRADICTION", "CONFIRMED"]
    assert res["contradiction_type"] in ["PAYMENT_TERM_CONFLICT", "DURATION_CONFLICT", "NUMERIC_VALUE_CONFLICT"]
    assert res["value_a"] == "30"
    assert res["value_b"] == "60"
    db.close()


def test_4_detect_permitted_vs_prohibited_policy():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-p1", filename="a.txt", safe_filename="a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-p2", filename="b.txt", safe_filename="b.txt", file_path="/tmp/b", file_type="txt", file_size=100)

    fact_a = {"topic": "External Data Sharing Policy", "fact_type": "BOOLEAN_POLICY", "value": "PERMITTED", "unit": "boolean", "statement": "External data sharing is permitted."}
    fact_b = {"topic": "External Data Sharing Policy", "fact_type": "BOOLEAN_POLICY", "value": "PROHIBITED", "unit": "boolean", "statement": "External data sharing is strictly prohibited."}

    res = contradiction_service.compare_facts(fact_a, fact_b, 0.95, doc_a, doc_b)
    assert res["status"] in ["CONTRADICTION", "CONFIRMED"]
    assert res["contradiction_type"] in ["POLICY_REQUIREMENT_CONFLICT", "OBLIGATION_CONFLICT"]
    db.close()


def test_5_detect_conflicting_dates():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-d1", filename="a.txt", safe_filename="a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-d2", filename="b.txt", safe_filename="b.txt", file_path="/tmp/b", file_type="txt", file_size=100)

    fact_a = {"topic": "Effective Date", "fact_type": "DATE", "value": "January 1, 2026", "unit": "date", "statement": "Effective from January 1, 2026."}
    fact_b = {"topic": "Effective Date", "fact_type": "DATE", "value": "March 1, 2026", "unit": "date", "statement": "Effective from March 1, 2026."}

    res = contradiction_service.compare_facts(fact_a, fact_b, 0.88, doc_a, doc_b)
    assert res["status"] in ["CONTRADICTION", "CONFIRMED"]
    assert res["contradiction_type"] == "DATE_CONFLICT"
    db.close()


def test_6_do_not_flag_unrelated_documents():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-u1", filename="a.txt", safe_filename="a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-u2", filename="b.txt", safe_filename="b.txt", file_path="/tmp/b", file_type="txt", file_size=100)

    fact_a = {"topic": "Termination Notice Period", "fact_type": "DURATION", "value": "30", "unit": "days", "statement": "30 days notice required."}
    fact_b = {"topic": "Data Retention Period", "fact_type": "DATA_RETENTION", "value": "30", "unit": "days", "statement": "Data retained for 30 days."}

    res = contradiction_service.compare_facts(fact_a, fact_b, 0.30, doc_a, doc_b)
    assert res["status"] in ["NO_CONTRADICTION", "DISMISSED"]
    db.close()


def test_7_do_not_flag_compatible_statements():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-c1", filename="sop_a.txt", safe_filename="sop_a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-c2", filename="sop_b.txt", safe_filename="sop_b.txt", file_path="/tmp/b", file_type="txt", file_size=100)

    fact_a = {"topic": "Termination Notice Period", "fact_type": "DURATION", "value": "30", "unit": "days", "statement": "30 days notice required."}
    fact_b = {"topic": "Termination Notice Period", "fact_type": "DURATION", "value": "30", "unit": "days", "statement": "30 days notice required."}

    res = contradiction_service.compare_facts(fact_a, fact_b, 0.98, doc_a, doc_b)
    assert res["status"] in ["NO_CONTRADICTION", "DISMISSED"]
    db.close()


def test_8_verify_contradiction_score_calculation():
    score, status = contradiction_service.calculate_contradiction_score(
        semantic_sim=0.90,
        numeric_conflict=1.0,
        negation_conflict=0.0,
        keyword_overlap=0.8,
        domain_rule=1.0
    )
    assert score >= 0.70
    assert status == "CONFIRMED"


def test_9_verify_evidence_preservation():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-e1", filename="a.txt", safe_filename="a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-e2", filename="b.txt", safe_filename="b.txt", file_path="/tmp/b", file_type="txt", file_size=100)
    db.add_all([doc_a, doc_b])

    chunk_a = DocumentChunk(chunk_id="ca_ev", document_id="doc-e1", chunk_index=0, page_number=4, section="Section 4", text="Vendors must provide 30 days notice.")
    chunk_b = DocumentChunk(chunk_id="cb_ev", document_id="doc-e2", chunk_index=0, page_number=7, section="Section 7", text="Vendors must provide 60 days notice.")
    db.add_all([chunk_a, chunk_b])
    db.commit()

    finding = ContradictionFinding(
        contradiction_id="c-ev-123",
        document_a_id=doc_a.document_id,
        document_b_id=doc_b.document_id,
        chunk_a_id=chunk_a.chunk_id,
        chunk_b_id=chunk_b.chunk_id,
        topic="Termination Notice Period",
        contradiction_type="TERMINATION_CONFLICT",
        status="CONFIRMED",
        statement_a=chunk_a.text,
        statement_b=chunk_b.text,
        value_a="30",
        value_b="60",
        unit="days",
        severity="MEDIUM",
        confidence=0.91,
        explanation="Both documents specify different notice periods.",
        evidence_a=chunk_a.text,
        evidence_b=chunk_b.text,
        page_a=4,
        page_b=7,
        section_a="Section 4",
        section_b="Section 7",
        source_a=doc_a.filename,
        source_b=doc_b.filename,
        source_filename_a=doc_a.filename,
        source_filename_b=doc_b.filename
    )
    db.add(finding)
    db.commit()

    saved = db.query(ContradictionFinding).filter(ContradictionFinding.contradiction_id == "c-ev-123").first()
    assert saved.page_a == 4
    assert saved.page_b == 7
    assert saved.section_a == "Section 4"
    assert saved.source_filename_a == "a.txt"
    db.close()


def test_10_verify_api_endpoints():
    file_a = SAMPLE_DIR / "policy_vendor_30_days.txt"
    file_b = SAMPLE_DIR / "policy_vendor_60_days.txt"

    with open(file_a, "rb") as f:
        content_a = f.read()
    with open(file_b, "rb") as f:
        content_b = f.read()

    up_res = client.post(
        "/documents/upload",
        files=[
            ("files", ("policy_vendor_30_days.txt", content_a, "text/plain")),
            ("files", ("policy_vendor_60_days.txt", content_b, "text/plain"))
        ]
    )
    assert up_res.status_code == 201
    docs = up_res.json()["uploaded_files"]
    doc_a_id = docs[0]["document_id"]
    doc_b_id = docs[1]["document_id"]

    # 1. POST /contradictions/detect
    det_res = client.post("/contradictions/detect", json={"document_ids": [doc_a_id, doc_b_id]})
    assert det_res.status_code == 200
    report = det_res.json()
    assert report["total_contradictions_detected"] >= 1

    # 2. POST /contradictions/compare
    comp_res = client.post("/contradictions/compare", json={"document_a_id": doc_a_id, "document_b_id": doc_b_id})
    assert comp_res.status_code == 200
    assert len(comp_res.json()) >= 1
    c_id = comp_res.json()[0]["contradiction_id"]

    # 3. GET /contradictions/{contradiction_id}
    single_res = client.get(f"/contradictions/{c_id}")
    assert single_res.status_code == 200
    assert single_res.json()["contradiction_id"] == c_id


def test_11_verify_status_update_api():
    db = TestingSessionLocal()
    doc1 = Document(document_id="doc1", filename="a.txt", safe_filename="a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc2 = Document(document_id="doc2", filename="b.txt", safe_filename="b.txt", file_path="/tmp/b", file_type="txt", file_size=100)
    db.add_all([doc1, doc2])
    db.commit()

    finding = ContradictionFinding(
        contradiction_id="c-status-test",
        document_a_id="doc1",
        document_b_id="doc2",
        topic="Termination Notice",
        contradiction_type="TERMINATION_CONFLICT",
        status="POTENTIAL",
        statement_a="30 days",
        statement_b="60 days",
        explanation="Test finding"
    )
    db.add(finding)
    db.commit()
    db.close()

    # PATCH /contradictions/{id}/status
    patch_res = client.patch("/contradictions/c-status-test/status", json={"status": "CONFIRMED"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "CONFIRMED"

    # Test invalid status
    invalid_res = client.patch("/contradictions/c-status-test/status", json={"status": "INVALID_STATUS"})
    assert invalid_res.status_code == 400


def test_12_verify_canonical_deduplication():
    key_ab = contradiction_service._canonical_key("docA", "chunk1", "docB", "chunk2", "Notice Period")
    key_ba = contradiction_service._canonical_key("docB", "chunk2", "docA", "chunk1", "Notice Period")
    assert key_ab == key_ba
