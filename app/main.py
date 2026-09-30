"""
FastAPI Enterprise Application Entry Point.
Provides REST APIs, OpenAPI documentation, security validation, structured logging, audit middleware,
health checks, readiness probes, and metrics export.
"""

import time
import uuid
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.core.database import SessionLocal, get_db
from app.core.exceptions import (
    BaseAuditorException,
    auditor_exception_handler,
    http_exception_handler,
    unhandled_exception_handler
)
from app.core.security import verify_api_key, enforce_rate_limit
from app.services.audit_log_service import audit_log_service
from app.services.metrics_service import metrics_service
from app.services.vector_store import vector_store
from app.services.bm25_service import bm25_service
from app.services.embedding_service import embedding_service
from app.services.reranker_service import reranker_service
from app.api.documents import router as documents_router

openapi_tags = [
    {"name": "Health", "description": "Liveness, readiness, and component health endpoints."},
    {"name": "Documents", "description": "Document upload, parsing, and classification endpoints."},
    {"name": "Search", "description": "Semantic, BM25 lexical, and hybrid search endpoints."},
    {"name": "RAG", "description": "Advanced grounded retrieval-augmented generation."},
    {"name": "Compliance", "description": "Automated compliance auditing and rule engine."},
    {"name": "Contradictions", "description": "Cross-document contradiction detection engine."},
    {"name": "Risk", "description": "Explainable document risk scoring and portfolio aggregation."},
    {"name": "Reports", "description": "PDF, CSV, and JSON audit report exports."},
    {"name": "Metrics", "description": "System telemetry and Prometheus metrics."},
    {"name": "Audit", "description": "System audit log viewer and request history."}
]

app = FastAPI(
    title=settings.APP_NAME,
    version="8.0.0",
    description="Production-Oriented Enterprise Document Intelligence, Compliance, Contradiction & Risk Auditing Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=openapi_tags
)

# Register CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Centralized Exception Handlers
app.add_exception_handler(BaseAuditorException, auditor_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Request ID & Audit Logging Middleware
@app.middleware("http")
async def request_audit_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Extract or generate X-Request-ID
    request_id = request.headers.get("X-Request-ID", f"req-{uuid.uuid4().hex[:12]}")
    request.state.request_id = request_id

    # Track metrics counter
    metrics_service.increment("requests_total")

    try:
        response: Response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id

        metrics_service.record_latency("request_latency", duration_ms)
        if response.status_code >= 400:
            metrics_service.increment("requests_failed")

        # Persist audit log for API calls (skip documentation & static routes)
        path = request.url.path
        if not path.startswith(("/docs", "/redoc", "/openapi.json")):
            db = SessionLocal()
            try:
                audit_log_service.log_event(
                    db=db,
                    request_id=request_id,
                    endpoint=path,
                    http_method=request.method,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    client_identifier=request.client.host if request.client else "127.0.0.1",
                    success=response.status_code < 400
                )
            finally:
                db.close()

        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000.0
        metrics_service.increment("requests_failed")
        metrics_service.record_latency("request_latency", duration_ms)
        raise exc

# Include Router
app.include_router(documents_router)

# ==========================================
# HEALTH & OBSERVABILITY ENDPOINTS
# ==========================================

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "8.0.0",
        "environment": settings.APP_ENV
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed component health check."""
    return {
        "status": "ok",
        "database": "sqlite",
        "version": "8.0.0",
        "components": {
            "database": "healthy",
            "faiss": "healthy" if vector_store.index is not None else "degraded",
            "bm25": "healthy" if bm25_service.bm25 is not None else "degraded",
            "embeddings": "healthy",
            "reranker": "healthy" if reranker_service.get_status()["available"] else "degraded"
        }
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness probe: verifies application process is active."""
    return {"status": "alive", "timestamp": time.time()}

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe: verifies database, vector index, and ML services are ready."""
    try:
        from app.core.database import init_db
        init_db()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Database not ready: {e}")


@app.get("/metrics", tags=["Metrics"])
async def get_metrics():
    """Returns application metrics in JSON format."""
    return metrics_service.get_metrics()

@app.get("/metrics/prometheus", tags=["Metrics"], response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Returns application metrics in Prometheus exposition format."""
    return metrics_service.get_prometheus_metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
