# ATS-Optimized Resume Bullet Points

## AI / ML Engineer
- Architected an enterprise-grade multi-document intelligence auditor combining **BM25 lexical search** and **FAISS dense vector store**, increasing Recall@5 to **20.1%** via **Cross-Encoder reranking** (`ms-marco-MiniLM-L-6-v2`).
- Developed a grounded **Retrieval-Augmented Generation (RAG)** pipeline with query intent classification, contextual deduplication, page-level citation tracing, and explicit abstention (`INSUFFICIENT_EVIDENCE`).
- Verified system reliability across a **102-query benchmark dataset** and maintained 100% pass rate over a **91-test pytest regression suite**.

## NLP / GenAI Engineer
- Engineered a hybrid retrieval engine integrating rank-bm25 and SentenceTransformers embeddings ($w_{\text{bm25}}=0.40, w_{\text{dense}}=0.60$) with min-max score normalization to eliminate vocabulary mismatch in legal agreements.
- Implemented an automated cross-document contradiction detector identifying numeric and temporal policy inconsistencies across vendor contracts with **0.936 F1-score**.
- Built an extractive answer generation module that provides traceable source document citations and prevents hallucinated responses.

## Data Engineer / Backend Engineer
- Designed a production-ready FastAPI REST architecture with constant-time API key security, sliding-window rate limiting, path traversal defenses, and secret-redacted audit logs.
- Integrated SQLAlchemy ORM database models, ReportLab PDF generation, Prometheus OpenMetrics endpoints (`/metrics/prometheus`), and request correlation IDs (`X-Request-ID`).
- Containerized the full application stack using multi-stage Docker and Docker Compose for reproducible local deployment.
