# Resume Project Entry Snippets (ATS-Optimized)

Use these verified project entry snippets on your resume, tailored to specific engineering roles.

---

## Option 1: AI / ML Engineer

**Enterprise Multi-Document Intelligence & Compliance Auditor** | *Python, FastAPI, FAISS, SentenceTransformers, BM25, Pytest, Docker*
* Engineered an end-to-end hybrid retrieval & compliance auditor combining BM25 lexical search and FAISS dense vector search via Reciprocal Rank Fusion (RRF), achieving sub-15ms hybrid retrieval latency on CPU.
* Integrated Cross-Encoder reranking (`ms-marco-MiniLM-L-6-v2`) and grounded RAG answer extraction, boosting Recall@5 to **20.1%** across a 102-query evaluation benchmark.
* Developed multi-strategy contradiction detection and weighted document risk scoring engines, processing multi-format documents (PDF, DOCX, TXT, OCR) with full citation traceability.
* Maintained **91/91 automated passing tests** covering unit, integration, failure injection, and recovery test suites.

---

## Option 2: NLP / GenAI Engineer

**Enterprise Multi-Document Intelligence & Compliance Auditor** | *Python, RAG, SentenceTransformers, Cross-Encoders, Streamlit, FastAPI*
* Implemented grounded RAG architecture with score-based abstention triggers ($\tau=0.25$) and exact passage citation mapping to eliminate hallucination in enterprise compliance queries.
* Implemented BM25 + FAISS hybrid retrieval with Reciprocal Rank Fusion, capturing both exact keyword matches and semantic paraphrasing across multi-document collections.
* Conducted reranker ablation study evaluating trade-offs between dense retrieval, hybrid fusion, and Cross-Encoder ranking across quality and latency dimensions.
* Built interactive Streamlit dashboard for real-time semantic search, RAG QA, cross-document contradiction inspection, and compliance risk reporting.

---

## Option 3: Backend / Systems Engineer

**Enterprise Multi-Document Intelligence & Compliance Auditor** | *Python, FastAPI, SQLAlchemy, SQLite, Prometheus, Docker, REST API*
* Architected RESTful API suite using FastAPI and Pydantic with RBAC API Key authentication, token-bucket rate limiting, and canonical path traversal defense.
* Implemented system-wide structured JSON logging with distributed request tracing, audit trail logging, and custom Prometheus telemetry endpoints.
* Designed fault-tolerant document ingestion pipeline supporting automated index recovery, transactional SQLite persistence, and zero-downtime index rebuilds.
* Containerized application stack using Docker & Docker Compose with multi-stage build optimization and automated health check probes.

---

## Option 4: Concise Single-Entry Block (General AI Engineer)

### **Enterprise Multi-Document Intelligence & Compliance Auditor**
* **Architecture**: Engineered a hybrid retrieval (BM25 + FAISS RRF) and compliance auditing platform using FastAPI, Streamlit, and SQLAlchemy.
* **Evaluation**: Benchmarked 102 queries across 10 categories, demonstrating sub-15ms retrieval latency and 20.1% Recall@5 with Cross-Encoder reranking.
* **Reliability & Security**: Hardened API security with RBAC keys, path traversal defenses, Prometheus metrics, and automated index recovery (**91/91 tests passing**).
