# Enterprise-Grade Multi-Document Intelligence & Compliance Auditor

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![FAISS](https://img.shields.io/badge/FAISS-Dense%20Search-orange.svg)](https://github.com/facebookresearch/faiss)
[![Test Suite](https://img.shields.io/badge/Tests-91%2F91%20Passing-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An end-to-end, production-oriented multi-document intelligence and compliance auditing system. Combines BM25 lexical search, FAISS dense vector retrieval, Cross-Encoder reranking (`ms-marco-MiniLM-L-6-v2`), grounded RAG with citations, deterministic compliance rule auditing, cross-document contradiction detection, explainable risk scoring, structured audit logging, Prometheus metrics, and a 15-module Streamlit dashboard.

---

## 1. System Architecture

```text
                    DOCUMENT INGESTION
             (PDF, DOCX, TXT, OCR, Scanned Images)
                               │
                               ▼
                    NLP & CHUNKING SERVICE
             (SpaCy, Cleaners, Dynamic Chunker)
                               │
                      ┌────────┴────────┐
                      ▼                 ▼
             BM25 SERVICE       FAISS VECTOR STORE
          (Lexical Inverted)   (SentenceTransformer)
                      │                 │
                      └────────┬────────┘
                               ▼
                     HYBRID SEARCH SERVICE
               (Reciprocal / Min-Max Fusion)
                               │
                               ▼
                    CROSS-ENCODER RERANKER
             (ms-marco-MiniLM-L-6-v2 / CPU Fallback)
                               │
                               ▼
                      ADVANCED RAG SERVICE
            (Query Analysis, Evidence Selection,
             Abstention, Grounding & Citations)
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
 COMPLIANCE ENGINE    CONTRADICTION ENGINE       RISK ENGINE
(Rule Matching &      (Cross-Doc Inconsistency    (Weighted Exposure
 Policy Auditing)       Detection Matrix)          Scoring Matrix)
        └──────────────────────┼──────────────────────┘
                               ▼
                      AUDIT & METRICS LOG
          (AuditLog Service, Redaction, Prometheus)
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
     STREAMLIT APP        REST API            PROMETHEUS
      (15 Modules)      (FastAPI)         (/metrics/prometheus)
```

---

## 2. Key Features

- **Multi-Format Ingestion**: Ingests PDFs, DOCX files, raw TXT, and scanned image documents via Tesseract OCR.
- **Hybrid Lexical + Semantic Search**: Combines BM25 Okapi inverted indexing ($w_{\text{bm25}}=0.40$) and 384-dimensional FAISS inner product dense search ($w_{\text{dense}}=0.60$) with min-max score normalization.
- **Cross-Encoder Reranking**: Re-scores candidate passages using `ms-marco-MiniLM-L-6-v2` with CPU batching and graceful fallback when disabled.
- **Grounded Advanced RAG**: Features intent analysis, contextual deduplication, citation generation, and explicit abstention (`INSUFFICIENT_EVIDENCE`) when retrieval confidence is below threshold.
- **Deterministic & Semantic Compliance Engine**: Evaluates documents against configurable JSON rules (presence, absence, threshold, regex, semantic match).
- **Cross-Document Contradiction Detection**: Automatically detects conflicting numerical limits, dates, payment schedules, or retention terms across independent files.
- **Explainable Document Risk Scoring**: Computes weighted risk exposure (0–100) across compliance failures, contradiction counts, and severity weights.
- **API Security & Governance**: Enforces constant-time `X-API-Key` authentication (`AUDITOR_API_KEY`), sliding-window rate limiting, path traversal defenses, and secret-redacted audit logs.
- **Observability & Metrics**: Exposes Prometheus metrics at `/metrics/prometheus` and detailed structured logs with request correlation IDs (`X-Request-ID`).
- **Interactive UI**: Includes a 15-module Streamlit dashboard for interactive search, RAG tracing, compliance reports, risk charts, and audit trails.

---

## 3. Verified Performance & Benchmarks

Evaluated across an expanded **102-query evaluation benchmark** (`data/evaluation/phase9_benchmark.json`):

| System Configuration | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | Latency (Avg) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FAISS Only** | 13.0% | 16.8% | 19.6% | 25.0% | 0.168 | 0.245 | 11.4 ms |
| **BM25 Only** | 7.6% | 14.1% | 15.8% | 21.7% | 0.118 | 0.183 | 0.2 ms |
| **Hybrid (BM25 + FAISS)** | 10.9% | 14.7% | 17.9% | 22.8% | 0.148 | 0.222 | 11.1 ms |
| **Hybrid + Cross-Encoder** | **8.2%** | **19.0%** | **20.1%** | **22.8%** | **0.144** | **0.231** | **442.8 ms** |

---

## 4. Quickstart Guide

### Environment Setup
```powershell
# 1. Create virtual environment
python -m venv .venv
..\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Initialize environment variables
copy .env.example .env
```

### Running the Test Suite & Benchmarks
```powershell
# Run 91-test regression suite
python -m pytest tests/ -q

# Run Phase 9 real-world evaluation runner
python scripts/run_phase9_evaluation.py

# Run security scanner
python scripts/security_check.py
```

### Running the REST API & Dashboard
```powershell
# Start FastAPI backend server (Port 8000)
uvicorn app.main:app --reload --port 8000

# Start Streamlit Frontend Dashboard (Port 8501)
streamlit run frontend/streamlit_app.py
```

---

## 5. Docker Deployment

```powershell
# Verify compose configuration
docker compose config

# Build and launch multi-container application
docker compose up --build -d
```

Access API at `http://localhost:8000/docs` and Streamlit at `http://localhost:8501`.

---

## 6. Project Structure

```text
enterprise-compliance-auditor/
├── app/
│   ├── api/             # FastAPI REST endpoint routes
│   ├── config.py        # Settings & YAML configuration loader
│   ├── core/            # Database ORM, security, logging
│   ├── models/          # SQLAlchemy ORM database models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # BM25, FAISS, Hybrid, Reranker, RAG, Compliance, Risk, Audit
│   └── utils/           # Text cleaning, PDF extraction helpers
├── configs/             # settings.yaml & compliance_rules.json
├── data/
│   ├── evaluation/      # 102-query benchmark dataset
│   └── vector_store/    # FAISS binary index & BM25 inverted index
├── docs/                # Methodological documentation & interview guides
├── frontend/            # Streamlit 15-module dashboard UI
├── reports/             # Empirical evaluation JSON, CSV, and markdown reports
├── research/            # Academic paper (MD/TeX), figures, and BibTeX citations
├── scripts/             # Evaluation, benchmarking, and security scripts
├── tests/               # 91 unit & integration pytest files
├── Dockerfile           # Multi-stage production container definition
├── docker-compose.yml   # Multi-service compose manifest
├── requirements.txt     # Runtime dependencies
└── README.md            # Repository overview
```

---

## 7. License & Research Citation

Distributed under the MIT License. See `LICENSE` for details.

```bibtex
@article{enterprise_compliance_auditor_2026,
  title={Enterprise-Grade Multi-Document Intelligence & Compliance Auditor: A Hybrid Retrieval Framework},
  author={AI & Compliance Engineering Team},
  year={2026}
}
```
