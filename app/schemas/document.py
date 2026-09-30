"""
Pydantic Schemas for Document Ingestion, Search, Indexing, and RAG APIs.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class DocumentChunkSchema(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class EntitySchema(BaseModel):
    entity_id: str
    document_id: str
    chunk_id: Optional[str] = None
    entity_text: str
    normalized_text: str
    entity_label: str
    start_position: int
    end_position: int
    context: Optional[str] = None
    confidence: Optional[float] = 1.0

    model_config = ConfigDict(from_attributes=True)


class DocumentSchema(BaseModel):
    document_id: str
    filename: str
    safe_filename: str
    file_type: str
    file_size: int
    upload_timestamp: Optional[str] = None
    document_status: str
    page_count: int
    ocr_required: bool
    processing_error: Optional[str] = None
    predicted_document_type: Optional[str] = "Unclassified"
    classification_confidence: Optional[float] = None
    chunks_count: int = 0
    entities_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailSchema(DocumentSchema):
    extracted_text: Optional[str] = None
    normalized_text: Optional[str] = None
    chunks: List[DocumentChunkSchema] = Field(default_factory=list)
    entities: List[EntitySchema] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    message: str
    uploaded_files: List[DocumentSchema]
    failed_files: List[Dict[str, str]] = Field(default_factory=list)


class DocumentProcessResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    file_type: str
    page_count: int
    chunks_created: int
    ocr_required: bool
    processing_error: Optional[str] = None


class ClassificationResponse(BaseModel):
    document_id: str
    filename: str
    predicted_document_type: str
    confidence: float
    status: str = "success"


class EntityListResponse(BaseModel):
    document_id: str
    filename: str
    total_entities: int
    entities: List[EntitySchema]


# ==========================================
# PHASE 4: SEARCH & RAG SCHEMAS
# ==========================================

class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    page_number: Optional[int] = None
    minimum_score: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    score: float
    text: str
    document_type: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]


class IndexStatusResponse(BaseModel):
    total_documents: int
    total_chunks: int
    indexed_chunks: int
    embedding_dimension: int
    index_type: str
    embedding_model: str


class IndexDocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunks_indexed: int
    status: str


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    minimum_score: float = Field(default=0.25, ge=0.0, le=1.0)


class RAGSourceItem(BaseModel):
    citation_index: int
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    relevance_score: float
    text: str


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    citations: List[str]
    sources: List[RAGSourceItem]
    retrieval_count: int
    max_score: float


# ==========================================
# PHASE 5: COMPLIANCE RULE ENGINE SCHEMAS
# ==========================================

class ComplianceRuleSchema(BaseModel):
    rule_id: str
    name: str
    description: str
    category: str
    severity: str
    enabled: bool = True
    requirement: str
    document_types: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    remediation: Optional[str] = None


class ComplianceFindingSchema(BaseModel):
    finding_id: str
    document_id: str
    rule_id: str
    status: str  # PASS, FAIL, NEEDS_REVIEW, NOT_APPLICABLE
    severity: str  # HIGH, MEDIUM, LOW
    title: str
    explanation: str
    evidence_text: Optional[str] = None
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_filename: Optional[str] = None
    relevance_score: Optional[float] = None
    remediation: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceSummarySchema(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    total_rules: int
    applicable_rules: int
    passed: int
    failed: int
    needs_review: int
    not_applicable: int
    findings: List[ComplianceFindingSchema] = Field(default_factory=list)


class ComplianceAuditRequest(BaseModel):
    document_ids: List[str]


# ==========================================
# PHASE 6: CONTRADICTION DETECTION SCHEMAS
# ==========================================

class DocumentEvidenceSchema(BaseModel):
    document_id: str
    filename: Optional[str] = None
    statement: str
    value: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None


class ContradictionFindingSchema(BaseModel):
    contradiction_id: str
    document_a_id: str
    document_b_id: str
    chunk_a_id: Optional[str] = None
    chunk_b_id: Optional[str] = None
    topic: str
    contradiction_type: str
    status: str
    statement_a: str
    statement_b: str
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    unit: Optional[str] = None
    scope_a: Optional[str] = None
    scope_b: Optional[str] = None
    severity: str
    confidence: float
    explanation: str
    page_a: Optional[int] = None
    page_b: Optional[int] = None
    section_a: Optional[str] = None
    section_b: Optional[str] = None
    source_filename_a: Optional[str] = None
    source_filename_b: Optional[str] = None
    document_a: Optional[DocumentEvidenceSchema] = None
    document_b: Optional[DocumentEvidenceSchema] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ContradictionDetectRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(default=None, description="Optional list of document IDs to analyze. If empty, audits all indexed documents.")


class PairwiseComparisonRequest(BaseModel):
    document_a_id: str
    document_b_id: str


class ContradictionStatusUpdate(BaseModel):
    status: str = Field(..., description="Status string: CONFIRMED, POTENTIAL, REVIEWED, DISMISSED")


class ContradictionSummarySchema(BaseModel):
    total_documents_analyzed: int
    total_contradictions_detected: int
    severity_metrics: Dict[str, int]
    type_breakdown: Dict[str, int]
    affected_documents_count: int
    affected_documents: List[str]
    contradictions: List[ContradictionFindingSchema]


# ==========================================
# PHASE 7: RISK SCORING & AUDIT SCHEMAS
# ==========================================

class RiskComponentSchema(BaseModel):
    raw_score: float
    weight: float
    weighted_score: float
    applicable_rules: Optional[int] = None
    passed_rules: Optional[int] = None
    failed_rules: Optional[int] = None
    review_rules: Optional[int] = None
    confirmed: Optional[int] = None
    potential: Optional[int] = None
    reviewed: Optional[int] = None


class RiskRecommendationSchema(BaseModel):
    recommendation_id: str
    priority: str
    title: str
    recommendation: str
    source: Optional[str] = None
    finding_id: Optional[str] = None
    finding_type: Optional[str] = None
    status: str = "OPEN"


class RiskAssessmentSchema(BaseModel):
    risk_assessment_id: str
    document_id: str
    filename: Optional[str] = None
    predicted_document_type: Optional[str] = None
    risk_score: float
    risk_level: str
    components: Dict[str, Any]
    high_findings_count: int
    medium_findings_count: int
    low_findings_count: int
    compliance_fail_count: int
    compliance_review_count: int
    confirmed_contradiction_count: int
    potential_contradiction_count: int
    risk_factors: List[str] = Field(default_factory=list)
    recommendations: List[RiskRecommendationSchema] = Field(default_factory=list)
    calculation_version: str = "1.0"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioRiskSchema(BaseModel):
    total_documents: int
    average_risk_score: float
    median_risk_score: float
    portfolio_risk_score: float
    portfolio_risk_level: str
    risk_distribution: Dict[str, int]
    high_risk_documents_count: int
    critical_risk_documents_count: int
    top_high_risk_documents: List[Dict[str, Any]]
    most_frequent_failed_rules: List[Dict[str, Any]]
    most_frequent_contradiction_topics: List[Dict[str, Any]]


class RiskRecalculateRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(default=None, description="Optional list of document IDs to recalculate risk for.")


# ==========================================
# PHASE 8: ENTERPRISE HARDENING & ADVANCED RAG SCHEMAS
# ==========================================

class HybridSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    bm25_weight: float = Field(default=0.40, ge=0.0, le=1.0)
    dense_weight: float = Field(default=0.60, ge=0.0, le=1.0)

class AdvancedRAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    bm25_weight: float = Field(default=0.40, ge=0.0, le=1.0)
    dense_weight: float = Field(default=0.60, ge=0.0, le=1.0)
    minimum_score: float = Field(default=0.15, ge=0.0, le=1.0)

class RetrievalTraceSchema(BaseModel):
    bm25_candidates: int
    dense_candidates: int
    fused_candidates: int
    reranked_candidates: int

class AdvancedRAGSourceItem(BaseModel):
    citation_index: int
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    score: float
    bm25_score: float = 0.0
    dense_score: float = 0.0
    reranker_score: float = 0.0
    text: str

class AdvancedRAGQueryResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    citations: List[str]
    sources: List[AdvancedRAGSourceItem]
    retrieval: RetrievalTraceSchema

class AuditLogSchema(BaseModel):
    log_id: str
    timestamp: str
    request_id: str
    client_identifier: Optional[str] = None
    endpoint: str
    http_method: str
    action: Optional[str] = None
    document_id: Optional[str] = None
    status_code: int
    duration_ms: float
    success: bool
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

class AuditLogListResponse(BaseModel):
    total: int
    logs: List[AuditLogSchema]

class HealthStatusResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]


PairwiseComparisonRequest.model_rebuild()
ContradictionStatusUpdate.model_rebuild()
ContradictionDetectRequest.model_rebuild()
ContradictionFindingSchema.model_rebuild()
RiskAssessmentSchema.model_rebuild()






