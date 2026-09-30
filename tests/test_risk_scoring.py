"""
Comprehensive Pytest Test Suite for Phase 7:
Explainable Risk Scoring Engine, Risk Assessment Models, Portfolio Analytics, Recommendations, PDF/CSV/JSON Report Exports, and FastAPI Endpoints.
"""

import pytest
import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.document import Document, DocumentChunk, ComplianceFinding, ContradictionFinding, RiskAssessment
from app.services.risk_scoring_service import risk_scoring_service
from app.services.risk_recommendation_service import risk_recommendation_service
from app.services.audit_report_service import audit_report_service

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_test_environment():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield

client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_1_risk_calculation_and_thresholds():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-r1", filename="policy.pdf", safe_filename="policy.pdf", file_path="/tmp/p", file_type="pdf", file_size=100)
    db.add(doc)

    f1 = ComplianceFinding(finding_id="f1", document_id="doc-r1", rule_id="RULE-001", status="FAIL", severity="HIGH", title="Missing Clause", explanation="Failed")
    f2 = ComplianceFinding(finding_id="f2", document_id="doc-r1", rule_id="RULE-002", status="PASS", severity="MEDIUM", title="Valid Clause", explanation="Passed")
    db.add_all([f1, f2])
    db.commit()

    res = risk_scoring_service.calculate_document_risk(db, "doc-r1")
    assert res["document_id"] == "doc-r1"
    assert res["risk_score"] > 0.0
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(res["risk_factors"]) >= 1
    assert "1 HIGH severity compliance rule(s) failed." in res["risk_factors"][0]
    db.close()


def test_2_compliance_component_weighting():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-comp-test", filename="c.pdf", safe_filename="c.pdf", file_path="/tmp/c", file_type="pdf", file_size=100)
    db.add(doc)

    # All PASS -> Compliance Component should be 0.0
    f1 = ComplianceFinding(finding_id="fc1", document_id="doc-comp-test", rule_id="RULE-001", status="PASS", severity="HIGH", title="Title 1", explanation="Pass")
    f2 = ComplianceFinding(finding_id="fc2", document_id="doc-comp-test", rule_id="RULE-002", status="PASS", severity="HIGH", title="Title 2", explanation="Pass")
    db.add_all([f1, f2])
    db.commit()

    res = risk_scoring_service.calculate_document_risk(db, "doc-comp-test")
    assert res["components"]["compliance"]["raw_score"] == 0.0
    assert res["risk_score"] == 0.0
    assert res["risk_level"] == "LOW"
    db.close()


def test_3_contradiction_component_weighting():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-ca", filename="a.txt", safe_filename="a.txt", file_path="/tmp/a", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-cb", filename="b.txt", safe_filename="b.txt", file_path="/tmp/b", file_type="txt", file_size=100)
    db.add_all([doc_a, doc_b])

    c1 = ContradictionFinding(
        contradiction_id="c-w1",
        document_a_id="doc-ca",
        document_b_id="doc-cb",
        topic="Notice Period",
        contradiction_type="DURATION_CONFLICT",
        status="CONFIRMED",
        statement_a="30 days",
        statement_b="60 days",
        severity="HIGH",
        confidence=0.95,
        explanation="Conflict"
    )
    db.add(c1)
    db.commit()

    res = risk_scoring_service.calculate_document_risk(db, "doc-ca")
    assert res["components"]["contradiction"]["raw_score"] > 0.0
    assert res["confirmed_contradiction_count"] == 1
    db.close()


def test_4_severity_and_review_components():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-sr", filename="sr.txt", safe_filename="sr.txt", file_path="/tmp/sr", file_type="txt", file_size=100)
    db.add(doc)

    f_review = ComplianceFinding(finding_id="fsr1", document_id="doc-sr", rule_id="RULE-005", status="NEEDS_REVIEW", severity="HIGH", title="Unclear Term", explanation="Needs review")
    db.add(f_review)
    db.commit()

    res = risk_scoring_service.calculate_document_risk(db, "doc-sr")
    assert res["components"]["review"]["raw_score"] > 0.0
    assert res["compliance_review_count"] == 1
    db.close()


def test_5_zero_applicable_findings_handling():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-zero", filename="empty.txt", safe_filename="empty.txt", file_path="/tmp/e", file_type="txt", file_size=100)
    db.add(doc)
    db.commit()

    res = risk_scoring_service.calculate_document_risk(db, "doc-zero")
    assert res["risk_score"] == 0.0
    assert res["risk_level"] == "LOW"
    assert res["components"]["compliance"]["applicable_rules"] == 0
    db.close()


def test_6_dismissed_contradictions_and_not_applicable():
    db = TestingSessionLocal()
    doc_a = Document(document_id="doc-dis1", filename="d1.txt", safe_filename="d1.txt", file_path="/tmp/d1", file_type="txt", file_size=100)
    doc_b = Document(document_id="doc-dis2", filename="d2.txt", safe_filename="d2.txt", file_path="/tmp/d2", file_type="txt", file_size=100)
    db.add_all([doc_a, doc_b])

    # NOT_APPLICABLE compliance finding
    f_na = ComplianceFinding(finding_id="fna", document_id="doc-dis1", rule_id="RULE-099", status="NOT_APPLICABLE", severity="HIGH", title="NA Rule", explanation="NA")
    # DISMISSED contradiction finding
    c_dis = ContradictionFinding(
        contradiction_id="cdis1", document_a_id="doc-dis1", document_b_id="doc-dis2",
        topic="Unrelated Topic", contradiction_type="OTHER", status="DISMISSED",
        statement_a="Statement A", statement_b="Statement B", explanation="Dismissed"
    )
    db.add_all([f_na, c_dis])
    db.commit()

    res = risk_scoring_service.calculate_document_risk(db, "doc-dis1")
    assert res["risk_score"] == 0.0
    assert res["risk_level"] == "LOW"
    db.close()


def test_7_portfolio_risk_aggregation():
    db = TestingSessionLocal()
    doc1 = Document(document_id="doc-p1", filename="p1.txt", safe_filename="p1.txt", file_path="/tmp/p1", file_type="txt", file_size=100)
    doc2 = Document(document_id="doc-p2", filename="p2.txt", safe_filename="p2.txt", file_path="/tmp/p2", file_type="txt", file_size=100)
    db.add_all([doc1, doc2])

    f1 = ComplianceFinding(finding_id="fp1", document_id="doc-p1", rule_id="RULE-001", status="FAIL", severity="HIGH", title="Fail 1", explanation="Fail")
    db.add(f1)
    db.commit()

    portfolio = risk_scoring_service.calculate_portfolio_risk(db)
    assert portfolio["total_documents"] >= 2
    assert "average_risk_score" in portfolio
    assert "portfolio_risk_score" in portfolio
    assert "risk_distribution" in portfolio
    db.close()


def test_8_recommendation_generation():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-rec", filename="rec.pdf", safe_filename="rec.pdf", file_path="/tmp/r", file_type="pdf", file_size=100)
    db.add(doc)

    f_fail = ComplianceFinding(finding_id="frec1", document_id="doc-rec", rule_id="RULE-003", status="FAIL", severity="HIGH", title="Termination Clause", explanation="Missing clause", remediation="Incorporate 30 days notice.")
    db.add(f_fail)
    db.commit()

    recs = risk_recommendation_service.generate_recommendations(db, "doc-rec")
    assert len(recs) >= 1
    assert recs[0]["priority"] == "HIGH"
    assert "RULE-003" in recs[0]["recommendation"]
    db.close()


def test_9_api_endpoints_risk_and_reports():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-api-risk", filename="api_risk.txt", safe_filename="api_risk.txt", file_path="/tmp/ar", file_type="txt", file_size=100)
    db.add(doc)
    db.commit()
    db.close()

    # 1. POST /documents/{id}/risk
    post_res = client.post("/documents/doc-api-risk/risk")
    assert post_res.status_code == 200
    assert post_res.json()["document_id"] == "doc-api-risk"

    # 2. GET /documents/{id}/risk
    get_res = client.get("/documents/doc-api-risk/risk")
    assert get_res.status_code == 200

    # 3. GET /documents/{id}/risk/breakdown
    breakdown_res = client.get("/documents/doc-api-risk/risk/breakdown")
    assert breakdown_res.status_code == 200
    assert "components" in breakdown_res.json()

    # 4. GET /risk/overview
    ov_res = client.get("/risk/overview")
    assert ov_res.status_code == 200
    assert "portfolio_risk_score" in ov_res.json()

    # 5. GET /risk/high-risk-documents
    hr_res = client.get("/risk/high-risk-documents?min_score=0.0")
    assert hr_res.status_code == 200

    # 6. GET /risk/recommendations
    recs_res = client.get("/risk/recommendations")
    assert recs_res.status_code == 200

    # 7. POST /risk/recalculate
    recalc_res = client.post("/risk/recalculate")
    assert recalc_res.status_code == 200


def test_10_pdf_report_generation():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-pdf", filename="pdf_test.pdf", safe_filename="pdf_test.pdf", file_path="/tmp/pdf", file_type="pdf", file_size=100)
    db.add(doc)
    db.commit()

    pdf_path = audit_report_service.generate_pdf_audit_report(db)
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")
    assert os.path.getsize(pdf_path) > 0
    db.close()


def test_11_csv_and_json_export():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-exp", filename="exp.txt", safe_filename="exp.txt", file_path="/tmp/e", file_type="txt", file_size=100)
    db.add(doc)
    db.commit()

    # JSON export test
    json_report = audit_report_service.generate_json_audit_report(db)
    assert "portfolio_summary" in json_report
    assert "documents" in json_report

    # CSV export test
    csv_report = audit_report_service.generate_csv_audit_report(db, export_type="risk_assessments")
    assert isinstance(csv_report, str)

    # GET /reports/audit/pdf endpoint test
    pdf_res = client.get("/reports/audit/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    db.close()


def test_12_repeat_risk_recalculation_and_persistence():
    db = TestingSessionLocal()
    doc = Document(document_id="doc-repeat", filename="rep.txt", safe_filename="rep.txt", file_path="/tmp/rep", file_type="txt", file_size=100)
    db.add(doc)
    db.commit()

    # First calculation
    res1 = risk_scoring_service.calculate_document_risk(db, "doc-repeat")
    # Second calculation (should update existing record without duplicates)
    res2 = risk_scoring_service.calculate_document_risk(db, "doc-repeat")

    count = db.query(RiskAssessment).filter(RiskAssessment.document_id == "doc-repeat").count()
    assert count == 1
    assert res1["risk_assessment_id"] == res2["risk_assessment_id"]
    db.close()
