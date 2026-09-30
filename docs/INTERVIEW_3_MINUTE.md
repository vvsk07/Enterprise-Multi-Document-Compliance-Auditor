# 3-Minute Technical Architecture Walkthrough

## Spoken Guide

> *"When auditing enterprise agreements, keyword-only search fails on semantic paraphrases, while pure vector search often misses exact numerical terms like '30 days notice' or 'Net 60 payment terms'. Furthermore, standard LLM RAG pipelines frequently hallucinate when evidence is absent.*
>
> *To address these challenges, I built an end-to-end multi-document auditor featuring a 5-stage architecture:*
>
> 1. **Ingestion & Preprocessing**: We ingest PDFs, DOCX, TXT, and scanned image files using PyMuPDF, python-docx, and Tesseract OCR. Texts are cleaned, classified, and split into overlapping chunks via SpaCy.
> 2. **Hybrid Candidate Retrieval**: Each chunk is indexed simultaneously into an inverted BM25 Okapi index for lexical matching and a 384-dimensional FAISS inner-product vector index using SentenceTransformers. We normalize raw scores using min-max scaling ($w_{\text{bm25}}=0.40, w_{\text{dense}}=0.60$) to merge candidate pools.
> 3. **Cross-Encoder Reranking**: Candidate passages are re-scored using `cross-encoder/ms-marco-MiniLM-L-6-v2`. Reranking improves Recall@5 from 17.9% to 20.1%. For latency-critical paths, reranking can be dynamically bypassed via configuration.
> 4. **Grounded RAG & Rule Auditing**: The RAG pipeline performs intent analysis, context deduplication, and sentence-level evidence selection. If no retrieved passage satisfies our minimum relevance threshold, the system abstains with `INSUFFICIENT_EVIDENCE`. Simultaneously, our compliance engine evaluates deterministic and semantic rules, while our contradiction engine detects conflicting clauses between documents using term-overlap candidate pairing.
> 5. **Governance & Telemetry**: The system is hardened with constant-time `X-API-Key` verification, sliding-window rate limiting, path traversal defenses, secret redaction, request correlation IDs (`X-Request-ID`), and Prometheus metrics at `/metrics/prometheus`.
>
> *I validated the platform using a 102-query evaluation suite and verified stability across a 91-test regression suite."*
