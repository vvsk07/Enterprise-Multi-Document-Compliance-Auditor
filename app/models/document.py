"""
SQLAlchemy Models for Document Ingestion, Text Chunks, and Extracted NLP Entities.
"""

from datetime import datetime, timezone
import json
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    safe_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, docx, txt
    file_size = Column(Integer, nullable=False)  # in bytes
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Status: UPLOADED, PROCESSING, PROCESSED, PARTIALLY_PROCESSED, FAILED, OCR_REQUIRED
    document_status = Column(String, default="UPLOADED", nullable=False)
    
    page_count = Column(Integer, default=0)
    ocr_required = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    extracted_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    # Classification fields
    predicted_document_type = Column(String, nullable=True)
    classification_confidence = Column(Float, nullable=True)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="document", cascade="all, delete-orphan")
    findings = relationship("ComplianceFinding", back_populates="document", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "safe_filename": self.safe_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "document_status": self.document_status,
            "page_count": self.page_count,
            "ocr_required": self.ocr_required,
            "processing_error": self.processing_error,
            "predicted_document_type": self.predicted_document_type or "Unclassified",
            "classification_confidence": round(self.classification_confidence, 4) if self.classification_confidence is not None else None,
            "chunks_count": len(self.chunks) if self.chunks else 0,
            "entities_count": len(self.entities) if self.entities else 0,
            "findings_count": len(self.findings) if self.findings else 0,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {}
        }


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)

    document = relationship("Document", back_populates="chunks")

    def to_dict(self):
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "section": self.section,
            "text": self.text,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {}
        }


class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String, ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"), nullable=True, index=True)
    entity_text = Column(String, nullable=False)
    normalized_text = Column(String, nullable=False)
    entity_label = Column(String, nullable=False)  # PERSON, ORG, GPE, DATE, MONEY, LAW, CONTRACT_ID, etc.
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    context = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)

    document = relationship("Document", back_populates="entities")

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "entity_text": self.entity_text,
            "normalized_text": self.normalized_text,
            "entity_label": self.entity_label,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "context": self.context,
            "confidence": self.confidence
        }


class ComplianceFinding(Base):
    __tablename__ = "compliance_findings"

    finding_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # PASS, FAIL, NEEDS_REVIEW, NOT_APPLICABLE
    severity = Column(String, nullable=False)  # HIGH, MEDIUM, LOW
    title = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_text = Column(Text, nullable=True)
    chunk_id = Column(String, ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"), nullable=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    source_filename = Column(String, nullable=True)
    relevance_score = Column(Float, nullable=True)
    remediation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="findings")

    def to_dict(self):
        return {
            "finding_id": self.finding_id,
            "document_id": self.document_id,
            "rule_id": self.rule_id,
            "status": self.status,
            "severity": self.severity,
            "title": self.title,
            "explanation": self.explanation,
            "evidence_text": self.evidence_text,
            "chunk_id": self.chunk_id,
            "page_number": self.page_number,
            "section": self.section,
            "source_filename": self.source_filename,
            "relevance_score": round(self.relevance_score, 4) if self.relevance_score is not None else None,
            "remediation": self.remediation,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ContradictionFinding(Base):
    __tablename__ = "contradiction_findings"

    contradiction_id = Column(String, primary_key=True, index=True)
    document_a_id = Column(String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    document_b_id = Column(String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_a_id = Column(String, ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"), nullable=True)
    chunk_b_id = Column(String, ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"), nullable=True)

    topic = Column(String, nullable=False, index=True)
    contradiction_type = Column(String, nullable=False)  # DURATION_CONFLICT, NUMERIC_VALUE_CONFLICT, DATE_CONFLICT, POLICY_REQUIREMENT_CONFLICT, BOOLEAN_REQUIREMENT_CONFLICT, JURISDICTION_CONFLICT, OTHER
    status = Column(String, default="CONTRADICTION", nullable=False)  # CONTRADICTION, POTENTIAL_CONTRADICTION, NO_CONTRADICTION, DIFFERENT_SCOPE

    statement_a = Column(Text, nullable=False)
    statement_b = Column(Text, nullable=False)
    value_a = Column(String, nullable=True)
    value_b = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    scope_a = Column(String, nullable=True)
    scope_b = Column(String, nullable=True)

    severity = Column(String, default="MEDIUM", nullable=False)  # HIGH, MEDIUM, LOW
    confidence = Column(Float, default=1.0)
    explanation = Column(Text, nullable=False)

    page_a = Column(Integer, nullable=True)
    page_b = Column(Integer, nullable=True)
    section_a = Column(String, nullable=True)
    section_b = Column(String, nullable=True)
    source_filename_a = Column(String, nullable=True)
    source_filename_b = Column(String, nullable=True)

    similarity_score = Column(Float, default=0.0)
    contradiction_score = Column(Float, default=0.0)
    evidence_a = Column(Text, nullable=True)
    evidence_b = Column(Text, nullable=True)
    source_a = Column(String, nullable=True)
    source_b = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "contradiction_id": self.contradiction_id,
            "document_a_id": self.document_a_id,
            "document_b_id": self.document_b_id,
            "chunk_a_id": self.chunk_a_id,
            "chunk_b_id": self.chunk_b_id,
            "topic": self.topic,
            "contradiction_type": self.contradiction_type,
            "status": self.status,
            "statement_a": self.statement_a,
            "statement_b": self.statement_b,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "unit": self.unit,
            "scope_a": self.scope_a,
            "scope_b": self.scope_b,
            "severity": self.severity,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "similarity_score": round(self.similarity_score, 4) if self.similarity_score is not None else 0.0,
            "contradiction_score": round(self.contradiction_score, 4) if self.contradiction_score is not None else 0.0,
            "explanation": self.explanation,
            "evidence_a": self.evidence_a or self.statement_a,
            "evidence_b": self.evidence_b or self.statement_b,
            "page_a": self.page_a,
            "page_b": self.page_b,
            "section_a": self.section_a,
            "section_b": self.section_b,
            "source_a": self.source_a or self.source_filename_a,
            "source_b": self.source_b or self.source_filename_b,
            "source_filename_a": self.source_filename_a or self.source_a,
            "source_filename_b": self.source_filename_b or self.source_b,
            "document_a": {
                "document_id": self.document_a_id,
                "filename": self.source_filename_a or self.source_a,
                "statement": self.statement_a,
                "value": self.value_a,
                "page": self.page_a,
                "section": self.section_a
            },
            "document_b": {
                "document_id": self.document_b_id,
                "filename": self.source_filename_b or self.source_b,
                "statement": self.statement_b,
                "value": self.value_b,
                "page": self.page_b,
                "section": self.section_b
            },
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    risk_assessment_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)

    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String, nullable=False, default="LOW")  # LOW, MEDIUM, HIGH, CRITICAL

    compliance_score = Column(Float, nullable=False, default=0.0)
    contradiction_score = Column(Float, nullable=False, default=0.0)
    severity_score = Column(Float, nullable=False, default=0.0)
    review_score = Column(Float, nullable=False, default=0.0)

    compliance_weight = Column(Float, nullable=False, default=0.45)
    contradiction_weight = Column(Float, nullable=False, default=0.30)
    severity_weight = Column(Float, nullable=False, default=0.15)
    review_weight = Column(Float, nullable=False, default=0.10)

    high_findings_count = Column(Integer, default=0)
    medium_findings_count = Column(Integer, default=0)
    low_findings_count = Column(Integer, default=0)

    compliance_fail_count = Column(Integer, default=0)
    compliance_review_count = Column(Integer, default=0)

    confirmed_contradiction_count = Column(Integer, default=0)
    potential_contradiction_count = Column(Integer, default=0)

    risk_factors_json = Column(Text, nullable=True)
    recommendations_json = Column(Text, nullable=True)
    components_breakdown_json = Column(Text, nullable=True)

    calculation_version = Column(String, default="1.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="risk_assessments")

    def to_dict(self):
        return {
            "risk_assessment_id": self.risk_assessment_id,
            "document_id": self.document_id,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "components": json.loads(self.components_breakdown_json) if self.components_breakdown_json else {
                "compliance": {"raw_score": self.compliance_score, "weight": self.compliance_weight, "weighted_score": round(self.compliance_score * self.compliance_weight, 2)},
                "contradiction": {"raw_score": self.contradiction_score, "weight": self.contradiction_weight, "weighted_score": round(self.contradiction_score * self.contradiction_weight, 2)},
                "severity": {"raw_score": self.severity_score, "weight": self.severity_weight, "weighted_score": round(self.severity_score * self.severity_weight, 2)},
                "review": {"raw_score": self.review_score, "weight": self.review_weight, "weighted_score": round(self.review_score * self.review_weight, 2)}
            },
            "high_findings_count": self.high_findings_count,
            "medium_findings_count": self.medium_findings_count,
            "low_findings_count": self.low_findings_count,
            "compliance_fail_count": self.compliance_fail_count,
            "compliance_review_count": self.compliance_review_count,
            "confirmed_contradiction_count": self.confirmed_contradiction_count,
            "potential_contradiction_count": self.potential_contradiction_count,
            "risk_factors": json.loads(self.risk_factors_json) if self.risk_factors_json else [],
            "recommendations": json.loads(self.recommendations_json) if self.recommendations_json else [],
            "calculation_version": self.calculation_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Alias for prompt compatibility
CrossDocumentContradiction = ContradictionFinding


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    request_id = Column(String, nullable=False, index=True)
    client_identifier = Column(String, nullable=True)
    endpoint = Column(String, nullable=False, index=True)
    http_method = Column(String, nullable=False)
    action = Column(String, nullable=True)
    document_id = Column(String, nullable=True, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    duration_ms = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    error_type = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "request_id": self.request_id,
            "client_identifier": self.client_identifier,
            "endpoint": self.endpoint,
            "http_method": self.http_method,
            "action": self.action,
            "document_id": self.document_id,
            "status_code": self.status_code,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            "error_type": self.error_type,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {}
        }





