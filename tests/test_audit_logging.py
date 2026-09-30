"""
Tests for Workstream 8: Audit Logging & Sanitization.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.audit_log_service import audit_log_service, sanitize_metadata
from app.models.document import AuditLog

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def test_sanitize_metadata_secrets():
    raw_meta = {
        "api_key": "secret-12345",
        "user": "test_admin",
        "nested": {"password": "my_password"}
    }
    clean = sanitize_metadata(raw_meta)
    assert clean["api_key"] == "[REDACTED]"
    assert clean["user"] == "test_admin"
    assert clean["nested"]["password"] == "[REDACTED]"

def test_audit_log_persistence_and_query():
    db = TestingSessionLocal()
    entry = audit_log_service.log_event(
        db=db,
        request_id="req-test-001",
        endpoint="/documents/upload",
        http_method="POST",
        status_code=201,
        duration_ms=45.2,
        action="DOCUMENT_UPLOAD",
        document_id="doc-123",
        metadata={"filename": "contract.pdf", "api_key": "secret"}
    )
    assert entry.log_id.startswith("audit-")

    logs = audit_log_service.get_logs(db, endpoint="/documents/upload")
    assert len(logs) == 1
    assert logs[0]["request_id"] == "req-test-001"
    assert logs[0]["metadata"]["api_key"] == "[REDACTED]"
    db.close()
