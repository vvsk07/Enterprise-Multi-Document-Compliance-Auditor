# API USAGE GUIDE

## Endpoints Summary

### Health & Observability
- `GET /health`: Component health status
- `GET /health/live`: Liveness check
- `GET /health/ready`: Readiness check
- `GET /metrics`: Application metrics JSON
- `GET /metrics/prometheus`: Prometheus metrics text

### Retrieval & RAG
- `POST /search`: FAISS semantic vector search
- `POST /search/hybrid`: BM25 + FAISS hybrid search
- `POST /rag/query`: Grounded RAG query
- `POST /rag/advanced`: Advanced Grounded RAG with candidate trace & confidence

### Compliance, Contradiction & Risk
- `POST /compliance/audit`: Run compliance audit
- `POST /contradictions/detect`: Cross-document contradiction scan
- `POST /risk/recalculate`: Recalculate document risk scores
- `GET /risk/overview`: Portfolio risk summary

### Audit & Security
- `GET /audit/logs`: Query audit events (filter by endpoint, action, status)
