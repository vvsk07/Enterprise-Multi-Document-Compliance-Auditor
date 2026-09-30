"""
Comprehensive Pytest Test Suite for Phase 3 NLP Pipeline:
TF-IDF Classification, spaCy NER, Entity Normalization, Metadata Extraction & API Endpoints.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.services.classification_service import classification_service, DocumentClassificationService
from app.services.ner_service import ner_service
from app.services.entity_service import entity_normalizer
from app.services.metadata_extractor import metadata_extractor
from app.models.document import Document, DocumentChunk, Entity

# Configure in-memory test database with StaticPool
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


def test_classifier_training_and_prediction():
    metrics = classification_service.train()
    assert "accuracy" in metrics
    assert metrics["accuracy"] > 0.50
    assert classification_service.classifier is not None
    assert classification_service.vectorizer is not None

    category, confidence = classification_service.predict(
        "This Mutual Non-Disclosure Agreement protects proprietary trade secrets."
    )
    assert category in ["NDA", "Contract", "Company Policy", "Other"]
    assert confidence >= 0.0


def test_classifier_low_confidence():
    service = DocumentClassificationService(confidence_threshold=0.99)
    category, confidence = service.predict("xyz abc unknown gibberish text")
    assert category == "Other"


def test_ner_extraction():
    text = "Acme Global Inc signed contract AGR-2026-100 with Vertex LLC on January 15, 2026 for $50,000 USD."
    entities = ner_service.extract_entities(text)
    assert len(entities) >= 3
    labels = [e["label"] for e in entities]
    assert "ORG" in labels or "CONTRACT_ID" in labels or "DATE" in labels


def test_entity_normalization():
    norm_org = entity_normalizer.normalize_entity_text("Acme Global Technologies Inc.", "ORG")
    assert "Inc" not in norm_org
    assert "Acme Global" in norm_org

    norm_person = entity_normalizer.normalize_entity_text("Dr. John Doe", "PERSON")
    assert "Dr." not in norm_person
    assert norm_person == "John Doe"


def test_metadata_extraction():
    text = "Agreement dated January 15, 2026 under Section 4.1 for amount $25,000 USD. Contact admin@acme.com."
    data = metadata_extractor.extract_metadata(text)
    assert len(data["dates"]) >= 1
    assert len(data["monetary_amounts"]) >= 1
    assert len(data["email_addresses"]) >= 1
    assert len(data["section_numbers"]) >= 1


def test_nlp_api_endpoints():
    # 1. Upload sample text document
    txt_path = SAMPLE_DIR / "compliant_contract.txt"
    with open(txt_path, "rb") as f:
        content = f.read()
    up_res = client.post(
        "/documents/upload",
        files=[("files", ("compliant_contract.txt", content, "text/plain"))]
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["uploaded_files"][0]["document_id"]

    # 2. Test POST /documents/{id}/classify
    cls_res = client.post(f"/documents/{doc_id}/classify")
    assert cls_res.status_code == 200
    cls_data = cls_res.json()
    assert cls_data["predicted_document_type"] in ["Contract", "NDA", "Compliance Document", "Other"]
    assert cls_data["confidence"] >= 0.0

    # 3. Test GET /documents/{id}/classification
    get_cls_res = client.get(f"/documents/{doc_id}/classification")
    assert get_cls_res.status_code == 200
    assert get_cls_res.json()["predicted_document_type"] == cls_data["predicted_document_type"]

    # 4. Test POST /documents/{id}/entities
    ent_res = client.post(f"/documents/{doc_id}/entities")
    assert ent_res.status_code == 200
    ent_data = ent_res.json()
    assert ent_data["total_entities"] > 0

    # 5. Test GET /documents/{id}/entities
    get_ent_res = client.get(f"/documents/{doc_id}/entities")
    assert get_ent_res.status_code == 200
    assert get_ent_res.json()["total_entities"] == ent_data["total_entities"]


def test_invalid_document_id():
    fake_id = "invalid-uuid-999"
    res1 = client.post(f"/documents/{fake_id}/classify")
    assert res1.status_code == 404

    res2 = client.post(f"/documents/{fake_id}/entities")
    assert res2.status_code == 404


def test_empty_text_nlp():
    # Test classifier on empty string
    cat, conf = classification_service.predict("")
    assert cat == "Other"
    assert conf == 0.0

    # Test NER on empty string
    ents = ner_service.extract_entities("")
    assert ents == []
