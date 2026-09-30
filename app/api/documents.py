"""
FastAPI API Routers for Document Management, Ingestion, NLP, Search, Vector Indexing, and RAG.
"""

import uuid
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Body, Query
from fastapi.responses import Response, FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db, init_db
from app.core.security import sanitize_filename, validate_file
from app.models.document import Document, DocumentChunk, Entity, ComplianceFinding, ContradictionFinding
from app.schemas.document import (
    DocumentSchema,
    DocumentDetailSchema,
    DocumentChunkSchema,
    EntitySchema,
    DocumentUploadResponse,
    DocumentProcessResponse,
    ClassificationResponse,
    EntityListResponse,
    SearchRequest,
    SearchResponse,
    IndexStatusResponse,
    IndexDocumentResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    ComplianceRuleSchema,
    ComplianceFindingSchema,
    ComplianceSummarySchema,
    ComplianceAuditRequest,
    ContradictionFindingSchema,
    ContradictionDetectRequest,
    PairwiseComparisonRequest,
    ContradictionStatusUpdate,
    RiskAssessmentSchema,
    PortfolioRiskSchema,
    RiskAssessmentSchema,
    PortfolioRiskSchema,
    RiskRecalculateRequest,
    HybridSearchRequest,
    AdvancedRAGQueryRequest,
    AdvancedRAGQueryResponse,
    AuditLogListResponse,
    AuditLogSchema
)
from app.services.document_processor import document_processor_service
from app.services.classification_service import classification_service
from app.services.ner_service import ner_service
from app.services.entity_service import entity_normalizer
from app.services.indexing_service import indexing_service
from app.services.search_service import search_service
from app.services.hybrid_search_service import hybrid_search_service
from app.services.advanced_rag_service import advanced_rag_service
from app.services.rag_service import rag_service
from app.services.compliance_engine import compliance_engine
from app.services.compliance_report_service import compliance_report_service
from app.services.contradiction_service import contradiction_service
from app.services.contradiction_report_service import contradiction_report_service
from app.services.risk_scoring_service import risk_scoring_service
from app.services.risk_recommendation_service import risk_recommendation_service
from app.services.audit_report_service import audit_report_service
from app.services.audit_log_service import audit_log_service

router = APIRouter(tags=["Documents & RAG Pipeline"])


# Initialize DB tables on load
init_db()

# ==========================================
# DOCUMENT INGESTION & MANAGEMENT ENDPOINTS
# ==========================================

@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload one or multiple documents (.pdf, .docx, .txt).
    Validates file extensions, size limits, sanitizes filenames to prevent path traversal,
    and automatically triggers text extraction, chunking, classification, NER, and vector indexing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    uploaded_docs: List[Document] = []
    failed_files = []

    for file in files:
        try:
            contents = await file.read()
            file_size = len(contents)
            original_filename = file.filename or "unnamed"
            
            is_valid, err_msg = validate_file(original_filename, file_size)
            if not is_valid:
                failed_files.append({"filename": original_filename, "error": err_msg})
                continue
                
            safe_name = sanitize_filename(original_filename)
            doc_id = str(uuid.uuid4())
            file_ext = Path(original_filename).suffix.lower().replace(".", "")
            
            save_path = settings.UPLOADS_DIR / f"{doc_id}_{safe_name}"
            with open(save_path, "wb") as f:
                f.write(contents)

            doc = Document(
                document_id=doc_id,
                filename=original_filename,
                safe_filename=safe_name,
                file_path=str(save_path.resolve()),
                file_type=file_ext,
                file_size=file_size,
                document_status="UPLOADED"
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            processed_doc = document_processor_service.process_document(db, doc_id)
            # Index document chunks in FAISS vector store
            indexing_service.index_document(db, doc_id)
            
            uploaded_docs.append(processed_doc)

        except Exception as e:
            failed_files.append({"filename": file.filename or "unknown", "error": str(e)})

    return DocumentUploadResponse(
        message=f"Uploaded, processed, and indexed {len(uploaded_docs)} document(s).",
        uploaded_files=[d.to_dict() for d in uploaded_docs],
        failed_files=failed_files
    )


@router.get("/documents", response_model=List[DocumentSchema])
async def list_documents(db: Session = Depends(get_db)):
    """
    Retrieves list of all uploaded documents and their processing/classification statuses.
    """
    docs = db.query(Document).order_by(Document.upload_timestamp.desc()).all()
    return [d.to_dict() for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentDetailSchema)
async def get_document_details(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves full details, extracted text, metadata, chunks, and entities for a single document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    doc_dict = doc.to_dict()
    doc_dict["extracted_text"] = doc.extracted_text
    doc_dict["normalized_text"] = doc.normalized_text
    doc_dict["chunks"] = [c.to_dict() for c in doc.chunks]
    doc_dict["entities"] = [e.to_dict() for e in doc.entities]

    return doc_dict


@router.post("/documents/{document_id}/process", response_model=DocumentProcessResponse)
async def process_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Explicitly triggers/re-runs text extraction, chunking, classification, NER, and vector indexing.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    processed_doc = document_processor_service.process_document(db, document_id)
    indexing_service.index_document(db, document_id)
    
    return DocumentProcessResponse(
        document_id=processed_doc.document_id,
        filename=processed_doc.filename,
        status=processed_doc.document_status,
        file_type=processed_doc.file_type,
        page_count=processed_doc.page_count,
        chunks_created=len(processed_doc.chunks),
        ocr_required=processed_doc.ocr_required,
        processing_error=processed_doc.processing_error
    )


# ==========================================
# NLP CLASSIFICATION & NER ENDPOINTS
# ==========================================

@router.post("/documents/{document_id}/classify", response_model=ClassificationResponse)
async def classify_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Triggers TF-IDF + Logistic Regression document classification for an ingested document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    text_to_classify = doc.normalized_text or doc.extracted_text or ""
    if not text_to_classify.strip():
        raise HTTPException(status_code=400, detail="Document contains no text for classification.")

    category, confidence = classification_service.predict(text_to_classify)
    doc.predicted_document_type = category
    doc.classification_confidence = confidence
    db.commit()

    return ClassificationResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        predicted_document_type=category,
        confidence=confidence
    )


@router.get("/documents/{document_id}/classification", response_model=ClassificationResponse)
async def get_document_classification_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves stored document classification result.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    return ClassificationResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        predicted_document_type=doc.predicted_document_type or "Unclassified",
        confidence=doc.classification_confidence or 0.0
    )


@router.post("/documents/{document_id}/entities", response_model=EntityListResponse)
async def extract_document_entities_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Runs spaCy NER & custom domain entity extraction on document text and saves entities to database.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    text = doc.normalized_text or doc.extracted_text or ""
    if not text.strip():
        return EntityListResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            total_entities=0,
            entities=[]
        )

    db.query(Entity).filter(Entity.document_id == document_id).delete()
    raw_entities = ner_service.extract_entities(text)
    db_entities = []

    for item in raw_entities:
        norm_text = entity_normalizer.normalize_entity_text(item["text"], item["label"])
        ent_obj = Entity(
            entity_id=str(uuid.uuid4()),
            document_id=doc.document_id,
            chunk_id=None,
            entity_text=item["text"],
            normalized_text=norm_text,
            entity_label=item["label"],
            start_position=item["start"],
            end_position=item["end"],
            context=item["context"]
        )
        db_entities.append(ent_obj)

    db.add_all(db_entities)
    db.commit()

    saved_entities = db.query(Entity).filter(Entity.document_id == document_id).all()
    return EntityListResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        total_entities=len(saved_entities),
        entities=[e.to_dict() for e in saved_entities]
    )


@router.get("/documents/{document_id}/entities", response_model=EntityListResponse)
async def get_document_entities_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves all stored NER entities for a document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    entities = db.query(Entity).filter(Entity.document_id == document_id).all()
    return EntityListResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        total_entities=len(entities),
        entities=[e.to_dict() for e in entities]
    )


# ==========================================
# VECTOR INDEXING, SEARCH & RAG ENDPOINTS
# ==========================================

@router.post("/search", response_model=SearchResponse)
async def semantic_search_endpoint(req: SearchRequest):
    """
    Executes dense vector semantic search against indexed document chunks with optional metadata filtering.
    """
    results = search_service.search(
        query=req.query,
        top_k=req.top_k,
        document_id=req.document_id,
        document_type=req.document_type,
        page_number=req.page_number,
        minimum_score=req.minimum_score
    )

    return SearchResponse(
        query=req.query,
        total_results=len(results),
        results=results
    )


@router.post("/documents/{document_id}/index", response_model=IndexDocumentResponse)
async def index_single_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Indexes or re-indexes vector embeddings for chunks of a single document into FAISS vector store.
    """
    res = indexing_service.index_document(db, document_id)
    return IndexDocumentResponse(**res)


@router.post("/index/rebuild", response_model=Dict[str, Any])
async def rebuild_vector_index_endpoint(db: Session = Depends(get_db)):
    """
    Rebuilds the FAISS vector index from scratch for all existing SQLite document chunks.
    """
    res = indexing_service.rebuild_index(db)
    return res


@router.get("/index/status", response_model=IndexStatusResponse)
async def get_vector_index_status_endpoint(db: Session = Depends(get_db)):
    """
    Returns total document, chunk, vector count, and embedding model statistics.
    """
    status = indexing_service.get_index_status(db)
    return IndexStatusResponse(**status)


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query_endpoint(req: RAGQueryRequest):
    """
    Executes grounded Retrieval-Augmented Generation (RAG) for user question and returns evidence citations.
    """
    res = rag_service.query_rag(
        question=req.query,
        top_k=req.top_k,
        document_id=req.document_id,
        document_type=req.document_type,
        minimum_score=req.minimum_score
    )

    return RAGQueryResponse(**res)


@router.post("/search/hybrid", response_model=SearchResponse)
async def hybrid_search_endpoint(req: HybridSearchRequest):
    """
    Executes hybrid retrieval combining BM25 lexical search and FAISS dense vector search with normalized fusion.
    """
    filters = {}
    if req.document_id:
        filters["document_id"] = req.document_id
    if req.document_type:
        filters["document_type"] = req.document_type

    results = hybrid_search_service.search(
        query=req.query,
        top_k=req.top_k,
        filters=filters if filters else None,
        bm25_weight=req.bm25_weight,
        dense_weight=req.dense_weight
    )

    return SearchResponse(
        query=req.query,
        total_results=len(results),
        results=results
    )


@router.post("/rag/advanced", response_model=AdvancedRAGQueryResponse)
async def advanced_rag_query_endpoint(req: AdvancedRAGQueryRequest):
    """
    Executes multi-stage Advanced Grounded RAG with candidate fusion, cross-encoder reranking, and full retrieval trace.
    """
    res = advanced_rag_service.query(
        question=req.query,
        top_k=req.top_k,
        document_id=req.document_id,
        document_type=req.document_type,
        bm25_weight=req.bm25_weight,
        dense_weight=req.dense_weight,
        minimum_score=req.minimum_score
    )

    return AdvancedRAGQueryResponse(**res)


@router.get("/audit/logs", response_model=AuditLogListResponse)
async def get_audit_logs_endpoint(
    endpoint: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    document_id: Optional[str] = Query(None),
    success_only: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves system audit log events with filtering by endpoint, action, document ID, success state, and pagination.
    """
    logs = audit_log_service.get_logs(
        db=db,
        endpoint=endpoint,
        action=action,
        document_id=document_id,
        success_only=success_only,
        limit=limit,
        offset=offset
    )

    return AuditLogListResponse(
        total=len(logs),
        logs=logs
    )



# ==========================================
# PHASE 5: COMPLIANCE RULE ENGINE ENDPOINTS
# ==========================================

@router.get("/compliance/rules", response_model=List[ComplianceRuleSchema])
async def get_compliance_rules_endpoint():
    """
    Returns list of all configured compliance rules.
    """
    rules = compliance_engine.get_rules()
    return rules


@router.get("/compliance/rules/{rule_id}", response_model=ComplianceRuleSchema)
async def get_compliance_rule_endpoint(rule_id: str):
    """
    Returns details for a single compliance rule by ID.
    """
    rule = compliance_engine.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Compliance rule with ID '{rule_id}' not found.")
    return rule


@router.post("/compliance/rules/reload", response_model=Dict[str, Any])
async def reload_compliance_rules_endpoint():
    """
    Reloads compliance rules from JSON configuration file without restarting application.
    """
    rules = compliance_engine.load_rules()
    return {
        "status": "success",
        "message": f"Reloaded {len(rules)} compliance rules from configuration.",
        "rules_count": len(rules)
    }


@router.post("/documents/{document_id}/compliance", response_model=ComplianceSummarySchema)
async def audit_document_compliance_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Executes compliance audit for a single document against configured compliance rules.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    compliance_engine.evaluate_document(db, document_id)
    summary = compliance_report_service.get_document_summary(db, document_id)
    return ComplianceSummarySchema(**summary)


@router.get("/documents/{document_id}/compliance", response_model=List[ComplianceFindingSchema])
async def get_document_compliance_findings_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves stored compliance findings for a single document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    findings = db.query(ComplianceFinding).filter(ComplianceFinding.document_id == document_id).all()
    return [f.to_dict() for f in findings]


@router.get("/documents/{document_id}/compliance/summary", response_model=ComplianceSummarySchema)
async def get_document_compliance_summary_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves compliance summary statistics and findings for a single document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    summary = compliance_report_service.get_document_summary(db, document_id)
    return ComplianceSummarySchema(**summary)


@router.post("/compliance/audit", response_model=Dict[str, Any])
async def audit_multiple_documents_endpoint(req: ComplianceAuditRequest, db: Session = Depends(get_db)):
    """
    Executes compliance audit for multiple documents and returns aggregate metrics and per-document summaries.
    """
    if not req.document_ids:
        raise HTTPException(status_code=400, detail="No document IDs provided for compliance audit.")

    compliance_engine.evaluate_documents(db, req.document_ids)
    report = compliance_report_service.get_multi_document_report(db, req.document_ids)
    return report


# ==========================================
# PHASE 6: CONTRADICTION DETECTION ENDPOINTS
# ==========================================

@router.post("/contradictions/detect", response_model=Dict[str, Any])
async def detect_contradictions_endpoint(req: Optional[ContradictionDetectRequest] = None, db: Session = Depends(get_db)):
    """
    Executes cross-document contradiction detection across selected or all indexed documents.
    """
    doc_ids = req.document_ids if req else None
    contradiction_service.find_contradictions(db, doc_ids)
    report = contradiction_report_service.get_contradictions_report(db, doc_ids)
    return report


@router.get("/contradictions", response_model=Dict[str, Any])
async def get_all_contradictions_endpoint(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    contradiction_type: Optional[str] = None,
    document_id: Optional[str] = None,
    minimum_score: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieves stored cross-document contradiction findings with optional query filtering.
    """
    report = contradiction_report_service.get_contradictions_report(db, [document_id] if document_id else None)
    findings = report.get("contradictions", [])

    filtered = []
    for f in findings:
        if severity and f["severity"].upper() != severity.upper():
            continue
        if status and f["status"].upper() != status.upper():
            continue
        if contradiction_type and f["contradiction_type"].upper() != contradiction_type.upper():
            continue
        if minimum_score is not None and (f.get("confidence", 0.0) or 0.0) < minimum_score:
            continue
        filtered.append(f)

    report["contradictions"] = filtered
    report["total_contradictions_detected"] = len(filtered)
    return report


@router.get("/documents/{document_id}/contradictions", response_model=List[ContradictionFindingSchema])
async def get_document_contradictions_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves stored contradiction findings involving a specific document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    findings = contradiction_service.find_document_contradictions(db, document_id)
    return [f.to_dict() for f in findings]


@router.post("/contradictions/detect/{document_id}", response_model=Dict[str, Any])
async def detect_document_contradictions_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Executes cross-document contradiction detection for a single document against all indexed repository documents.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    all_docs = db.query(Document).all()
    all_doc_ids = [d.document_id for d in all_docs]
    if document_id not in all_doc_ids:
        all_doc_ids.append(document_id)

    contradiction_service.find_contradictions(db, all_doc_ids)
    findings = contradiction_service.find_document_contradictions(db, document_id)
    return {
        "document_id": document_id,
        "filename": doc.filename,
        "total_contradictions_found": len(findings),
        "contradictions": [f.to_dict() for f in findings]
    }


@router.post("/documents/{document_id}/contradictions", response_model=List[ContradictionFindingSchema])
async def post_document_contradictions_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Finds and returns contradiction findings involving one document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    all_docs = db.query(Document).all()
    all_ids = [d.document_id for d in all_docs]
    contradiction_service.find_contradictions(db, all_ids)
    findings = contradiction_service.find_document_contradictions(db, document_id)
    return [f.to_dict() for f in findings]


@router.post("/contradictions/compare", response_model=List[ContradictionFindingSchema])
async def compare_two_documents_endpoint(req: PairwiseComparisonRequest, db: Session = Depends(get_db)):
    """
    Executes pairwise contradiction detection between document_a_id and document_b_id.
    """
    doc_a = db.query(Document).filter(Document.document_id == req.document_a_id).first()
    doc_b = db.query(Document).filter(Document.document_id == req.document_b_id).first()
    if not doc_a or not doc_b:
        raise HTTPException(status_code=404, detail="One or both specified document IDs were not found.")

    findings = contradiction_service.find_pairwise_contradictions(db, req.document_a_id, req.document_b_id)
    return [f.to_dict() for f in findings]


@router.get("/contradictions/{contradiction_id}", response_model=ContradictionFindingSchema)
async def get_single_contradiction_endpoint(contradiction_id: str, db: Session = Depends(get_db)):
    """
    Retrieves complete evidence for a single contradiction finding.
    """
    finding = db.query(ContradictionFinding).filter(ContradictionFinding.contradiction_id == contradiction_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"Contradiction finding with ID '{contradiction_id}' not found.")
    return finding.to_dict()


@router.patch("/contradictions/{contradiction_id}/status", response_model=ContradictionFindingSchema)
async def update_contradiction_status_endpoint(contradiction_id: str, req: ContradictionStatusUpdate, db: Session = Depends(get_db)):
    """
    Updates status of a contradiction finding (CONFIRMED, POTENTIAL, REVIEWED, DISMISSED).
    """
    valid_statuses = ["CONFIRMED", "POTENTIAL", "REVIEWED", "DISMISSED"]
    if req.status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status '{req.status}'. Must be one of {valid_statuses}")

    finding = db.query(ContradictionFinding).filter(ContradictionFinding.contradiction_id == contradiction_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"Contradiction finding with ID '{contradiction_id}' not found.")

    finding.status = req.status.upper()
    db.commit()
    db.refresh(finding)
    return finding.to_dict()


# ==========================================
# PHASE 7: RISK SCORING & AUDIT ENDPOINTS
# ==========================================

@router.post("/documents/{document_id}/risk", response_model=RiskAssessmentSchema)
async def calculate_document_risk_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Calculates or refreshes risk assessment for a single document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    res = risk_scoring_service.calculate_document_risk(db, document_id)
    return res


@router.get("/documents/{document_id}/risk", response_model=RiskAssessmentSchema)
async def get_document_risk_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieves stored or computed risk assessment for a single document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    res = risk_scoring_service.get_risk_breakdown(db, document_id)
    return res


@router.get("/documents/{document_id}/risk/breakdown", response_model=Dict[str, Any])
async def get_document_risk_breakdown_endpoint(document_id: str, db: Session = Depends(get_db)):
    """
    Returns detailed explainable risk calculation breakdown for a single document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    res = risk_scoring_service.get_risk_breakdown(db, document_id)
    return res


@router.post("/risk/recalculate", response_model=Dict[str, Any])
async def recalculate_risk_endpoint(req: Optional[RiskRecalculateRequest] = None, db: Session = Depends(get_db)):
    """
    Recalculates risk assessment for multiple or all documents in the repository.
    """
    if req and req.document_ids:
        updated = []
        for doc_id in req.document_ids:
            res = risk_scoring_service.calculate_document_risk(db, doc_id)
            updated.append(res)
        return {
            "status": "success",
            "message": f"Successfully recalculated risk for {len(updated)} specified document(s).",
            "recalculated_count": len(updated)
        }
    return risk_scoring_service.recalculate_all_risks(db)


@router.get("/risk/overview", response_model=PortfolioRiskSchema)
async def get_portfolio_risk_overview_endpoint(db: Session = Depends(get_db)):
    """
    Returns portfolio-level aggregate risk statistics, distribution, and top high-risk documents.
    """
    res = risk_scoring_service.calculate_portfolio_risk(db)
    return res


@router.get("/risk/statistics", response_model=PortfolioRiskSchema)
async def get_risk_statistics_endpoint(db: Session = Depends(get_db)):
    """
    Alias endpoint for portfolio risk statistics.
    """
    res = risk_scoring_service.calculate_portfolio_risk(db)
    return res


@router.get("/risk/high-risk-documents", response_model=List[RiskAssessmentSchema])
async def get_high_risk_documents_endpoint(min_score: float = Query(50.0, ge=0.0, le=100.0), db: Session = Depends(get_db)):
    """
    Retrieves risk assessments for documents scoring above the specified minimum risk threshold.
    """
    portfolio = risk_scoring_service.calculate_portfolio_risk(db)
    docs = db.query(Document).all()
    high_risk_assessments = []

    for d in docs:
        res = risk_scoring_service.get_risk_breakdown(db, d.document_id)
        if res.get("risk_score", 0.0) >= min_score:
            high_risk_assessments.append(res)

    high_risk_assessments.sort(key=lambda x: x.get("risk_score", 0.0), reverse=True)
    return high_risk_assessments


@router.get("/risk/recommendations", response_model=List[Dict[str, Any]])
async def get_all_recommendations_endpoint(document_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns actionable risk recommendations across all or selected documents.
    """
    if document_id:
        return risk_recommendation_service.generate_recommendations(db, document_id)

    docs = db.query(Document).all()
    all_recs = []
    for d in docs:
        recs = risk_recommendation_service.generate_recommendations(db, d.document_id)
        all_recs.extend(recs)
    return all_recs


@router.get("/reports/audit", response_model=Dict[str, Any])
async def get_audit_report_data_endpoint(db: Session = Depends(get_db)):
    """
    Generates complete structured audit report dataset.
    """
    return audit_report_service.generate_json_audit_report(db)


@router.get("/reports/audit/json", response_model=Dict[str, Any])
async def get_json_audit_report_endpoint(db: Session = Depends(get_db)):
    """
    Export audit report in JSON format.
    """
    return audit_report_service.generate_json_audit_report(db)


@router.get("/reports/audit/csv")
async def get_csv_audit_report_endpoint(export_type: str = Query("risk_assessments", description="Export type: risk_assessments, compliance_findings, contradictions"), db: Session = Depends(get_db)):
    """
    Export audit data in CSV format.
    """
    csv_content = audit_report_service.generate_csv_audit_report(db, export_type=export_type)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={export_type}_report.csv"}
    )


@router.get("/reports/audit/pdf")
async def get_pdf_audit_report_endpoint(db: Session = Depends(get_db)):
    """
    Generates and returns downloadable PDF audit report document.
    """
    pdf_path = audit_report_service.generate_pdf_audit_report(db)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path)
    )





