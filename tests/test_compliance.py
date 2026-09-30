"""
Comprehensive Pytest Test Suite for Phase 5:
Compliance Rule Engine, Evaluation Types, Finding Generation, API Endpoints, and Summaries.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.services.compliance_engine import compliance_engine
from app.services.compliance_report_service import compliance_report_service
from app.models.document import Document, DocumentChunk, ComplianceFinding

# In-memory SQLite database setup with StaticPool for thread-safe test execution
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

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_rule_loading_and_schema():
    rules = compliance_engine.load_rules()
    assert len(rules) >= 10
    
    rule1 = compliance_engine.get_rule_by_id("RULE-001")
    assert rule1 is not None
    assert rule1["rule_id"] == "RULE-001"
    assert rule1["name"] == "Confidentiality Clause"
    assert rule1["severity"] == "HIGH"
    assert "Contract" in (rule1.get("document_types") or rule1.get("required_for", []))

    invalid_rule = compliance_engine.get_rule_by_id("NONEXISTENT_RULE_999")
    assert invalid_rule is None


def test_rule_applicability():
    rule = compliance_engine.get_rule_by_id("RULE-001") # applies to Contract, NDA
    assert compliance_engine.is_rule_applicable(rule, "Contract") is True
    assert compliance_engine.is_rule_applicable(rule, "NDA") is True
    assert compliance_engine.is_rule_applicable(rule, "Invoice", filename="invoice_001.pdf") is False


def test_evaluation_scenarios():
    db = TestingSessionLocal()
    
    # 1. Create a dummy compliant document
    compliant_doc = Document(
        document_id="doc-test-compliant",
        filename="sample_contract.txt",
        safe_filename="sample_contract.txt",
        file_path="/tmp/sample_contract.txt",
        file_type="txt",
        file_size=1024,
        document_status="PROCESSED",
        predicted_document_type="Contract",
        extracted_text="THIS MASTER SERVICES AGREEMENT is dated as of January 1, 2026, entered into by and between Company A and Company B. Both parties agree to maintain strict confidentiality of all proprietary information. Either party may terminate this agreement with 30 days written notice. Governing law shall be the courts of New York. Data retention is retained for 5 years.",
        normalized_text="this master services agreement is dated as of january 1 2026 entered into by and between company a and company b both parties agree to maintain strict confidentiality of all proprietary information either party may terminate this agreement with 30 days written notice governing law shall be the courts of new york data retention is retained for 5 years"
    )
    db.add(compliant_doc)
    db.commit()

    # Evaluate compliant document
    findings = compliance_engine.evaluate_document(db, compliant_doc.document_id)
    assert len(findings) >= 10
    
    # Check RULE-001 (Confidentiality) -> PASS
    f_conf = next(f for f in findings if f.rule_id == "RULE-001")
    assert f_conf.status == "PASS"
    assert "confidentiality" in (f_conf.evidence_text or "").lower()

    # Check RULE-003 (Termination) -> PASS
    f_term = next(f for f in findings if f.rule_id == "RULE-003")
    assert f_term.status in ["PASS", "NEEDS_REVIEW"]

    # Check RULE-010 (Data Retention Threshold) -> PASS (5 years <= 10 years)
    f_ret = next(f for f in findings if f.rule_id == "RULE-010")
    assert f_ret.status in ["PASS", "NOT_APPLICABLE", "NEEDS_REVIEW"]

    # 2. Create a dummy non-compliant document missing required clauses
    non_compliant_doc = Document(
        document_id="doc-test-missing",
        filename="bad_contract.txt",
        safe_filename="bad_contract.txt",
        file_path="/tmp/bad_contract.txt",
        file_type="txt",
        file_size=512,
        document_status="PROCESSED",
        predicted_document_type="Contract",
        extracted_text="Simple work note without any legal terms or agreement details.",
        normalized_text="simple work note without any legal terms or agreement details"
    )
    db.add(non_compliant_doc)
    db.commit()

    findings_bad = compliance_engine.evaluate_document(db, non_compliant_doc.document_id)
    f_conf_bad = next(f for f in findings_bad if f.rule_id == "RULE-001")
    assert f_conf_bad.status in ["FAIL", "NEEDS_REVIEW"]

    db.close()


def test_compliance_summary_service():
    db = TestingSessionLocal()
    summary = compliance_report_service.get_document_summary(db, "doc-test-compliant")
    assert summary["document_id"] == "doc-test-compliant"
    assert summary["total_rules"] >= 10
    assert summary["passed"] >= 1
    assert "findings" in summary
    db.close()


def test_compliance_api_endpoints():
    # 1. Upload sample document to trigger full pipeline
    txt_path = SAMPLE_DIR / "compliant_contract.txt"
    with open(txt_path, "rb") as f:
        content = f.read()
    up_res = client.post(
        "/documents/upload",
        files=[("files", ("compliant_contract.txt", content, "text/plain"))]
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["uploaded_files"][0]["document_id"]

    # 2. Test GET /compliance/rules
    rules_res = client.get("/compliance/rules")
    assert rules_res.status_code == 200
    assert len(rules_res.json()) >= 10

    # 3. Test GET /compliance/rules/{rule_id}
    rule_res = client.get("/compliance/rules/RULE-001")
    assert rule_res.status_code == 200
    assert rule_res.json()["name"] == "Confidentiality Clause"

    # 4. Test POST /documents/{id}/compliance
    audit_res = client.post(f"/documents/{doc_id}/compliance")
    assert audit_res.status_code == 200
    aud_data = audit_res.json()
    assert aud_data["document_id"] == doc_id
    assert aud_data["passed"] >= 1

    # 5. Test GET /documents/{id}/compliance
    find_res = client.get(f"/documents/{doc_id}/compliance")
    assert find_res.status_code == 200
    assert len(find_res.json()) >= 10

    # 6. Test GET /documents/{id}/compliance/summary
    sum_res = client.get(f"/documents/{doc_id}/compliance/summary")
    assert sum_res.status_code == 200
    assert sum_res.json()["total_rules"] >= 10

    # 7. Test POST /compliance/audit (multi-document)
    multi_res = client.post("/compliance/audit", json={"document_ids": [doc_id]})
    assert multi_res.status_code == 200
    m_data = multi_res.json()
    assert m_data["audited_documents"] == 1

    # 8. Test POST /compliance/rules/reload
    reload_res = client.post("/compliance/rules/reload")
    assert reload_res.status_code == 200
    assert reload_res.json()["status"] == "success"


def test_compliance_api_edge_cases():
    # Test invalid document ID
    res = client.post("/documents/invalid-id-999/compliance")
    assert res.status_code == 404

    # Test invalid rule ID
    rule_res = client.get("/compliance/rules/INVALID-RULE-999")
    assert rule_res.status_code == 404

    # Test empty multi-audit list
    empty_audit = client.post("/compliance/audit", json={"document_ids": []})
    assert empty_audit.status_code == 400
