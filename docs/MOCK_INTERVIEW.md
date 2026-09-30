# 30-Question Mock Technical Interview Guide

This guide simulates a 10-round comprehensive technical interview covering Python, NLP, Retrieval, RAG, Machine Learning, Backend Engineering, System Design, Security, and Project Defense based on the **Enterprise-Grade Multi-Document Intelligence & Compliance Auditor**.

---

## Round 1 — Project Introduction

### Q1: Can you introduce your project in 60 seconds?
* **Expected Answer**: Focus on the problem (manual policy compliance & document auditing), the technical solution (Hybrid BM25 + FAISS retrieval, Cross-Encoder reranking, extractive RAG, deterministic contradiction detection, compliance engine, risk scoring), and key verified achievements (102-query benchmark evaluation, sub-15ms hybrid latency, 91 automated tests passing).
* **Common Mistake**: Getting bogged down in minor implementation details or claiming vague "100% accuracy" without empirical benchmark context.
* **Follow-up**: What was the single hardest engineering challenge you faced?

### Q2: Why did you build a hybrid retrieval system instead of relying purely on vector embeddings?
* **Expected Answer**: Dense embeddings excel at semantic similarity but frequently fail on exact keyword codes, quantitative thresholds, or specific policy identifiers (e.g., `ISO-27001-5.2`). BM25 handles exact term matching, while FAISS handles semantic paraphrasing. Reciprocal Rank Fusion (RRF) combines both effectively.
* **Common Mistake**: Stating vector search is always inferior or failing to explain RRF fusion.
* **Follow-up**: Did hybrid search outperform single retrieval methods across all query categories?

### Q3: What is the high-level architecture of your compliance auditing engine?
* **Expected Answer**: Document Ingestion $\rightarrow$ Processing & Chunking $\rightarrow$ Hybrid Retrieval & Reranking $\rightarrow$ Extractive RAG Answer Generation $\rightarrow$ Compliance Rule Evaluation & Contradiction Detection $\rightarrow$ Weighted Risk Scoring $\rightarrow$ Audit Log Logging & API/UI Presentation.
* **Common Mistake**: Confusing the compliance rule engine with the vector retrieval module.
* **Follow-up**: How do you prevent hallucinated compliance violations?

---

## Round 2 — Python

### Q4: How do you handle concurrency and CPU-bound tasks in FastAPI?
* **Expected Answer**: I/O-bound tasks (database queries, network calls) use `async/await` coroutines on FastAPI's event loop. Heavy CPU-bound tasks (SentenceTransformer vector encoding, Cross-Encoder inference, FAISS indexing) are offloaded to worker threads via `run_in_threadpool` or background task queues to avoid blocking the main event loop.
* **Common Mistake**: Declaring heavy CPU-bound functions as `async def` without thread offloading, which freezes the event loop.
* **Follow-up**: How would you scale this execution across multiple process workers?

### Q5: How is memory managed when building FAISS indexes over millions of chunks?
* **Expected Answer**: Raw numpy embedding arrays are generated in streaming batches rather than loaded into memory all at once. For massive scale, `faiss.IndexIVFFlat` or `IndexHNSW` reduces RAM consumption compared to uncompressed `IndexFlatIP`.
* **Common Mistake**: Assuming Python's garbage collector instantly frees memory during large numpy array allocations.
* **Follow-up**: What is the memory footprint of a 384-dimensional float32 vector?

### Q6: How do custom pytest fixtures improve your test architecture?
* **Expected Answer**: Fixtures in `conftest.py` instantiate modular test databases (using SQLite in-memory), mock vector indexes, temporary test document sets, and pre-configured FastAPI test clients. This guarantees test isolation, prevents state contamination, and speeds up test suite execution (91 tests in ~32s).
* **Common Mistake**: Creating persistent side-effects on disk during test runs without cleanup.
* **Follow-up**: How do you mock external LLM inference during automated testing?

---

## Round 3 — Natural Language Processing

### Q7: Explain the difference between Bi-Encoders and Cross-Encoders.
* **Expected Answer**: Bi-Encoders map queries and documents into independent vectors, enabling sub-linear ANN search via cosine similarity (fast, scalable). Cross-Encoders feed `(Query, Passage)` pairs together through self-attention, allowing full token-to-token cross-interaction (higher accuracy, but computationally expensive).
* **Common Mistake**: Believing Cross-Encoders can be pre-indexed into vector databases.
* **Follow-up**: What was the measured latency difference between Bi-Encoder search and Cross-Encoder reranking in your benchmark?

### Q8: How does text chunking impact retrieval precision?
* **Expected Answer**: Overly large chunks (e.g., 2000 words) dilute specific semantic vectors and cause noisy context insertion. Overly small chunks (e.g., 50 words) fragment context and break sentence dependencies. A 512-character window with a 50-character overlap maintains sentence integrity while preserving vector specificity.
* **Common Mistake**: Failing to implement chunk overlap, causing loss of boundary context.
* **Follow-up**: Did you test semantic boundary chunking vs fixed-length chunking?

### Q9: What model did you use for embeddings, and why?
* **Expected Answer**: `sentence-transformers/all-MiniLM-L6-v2`. It produces 384-dimensional dense vectors with an excellent trade-off between inference speed (~14ms on CPU) and retrieval quality on standard benchmarks (MTEB).
* **Common Mistake**: Selecting a massive 7B parameter model for simple retrieval tasks without justifying hardware constraints.
* **Follow-up**: How would you handle domain adaptation for specialized legal or financial jargon?

---

## Round 4 — Retrieval & Vector Search

### Q10: How does Reciprocal Rank Fusion (RRF) aggregate BM25 and FAISS results?
* **Expected Answer**: RRF takes ranked positions rather than raw uncalibrated similarity scores. For passage $d$, score is $RRF(d) = \sum_{m \in \{BM25, FAISS\}} \frac{1}{k + r_m(d)}$ with $k=60$. This avoids score normalization issues between unbounded BM25 scores and cosine similarity probabilities.
* **Common Mistake**: Linearly adding raw BM25 scores to FAISS cosine similarities.
* **Follow-up**: Why is raw score addition dangerous?

### Q11: What metric did you use to evaluate retrieval quality, and why?
* **Expected Answer**: Recall@K (K=1,3,5,10), Precision@K, MRR (Mean Reciprocal Rank), and nDCG@5/10. Recall@K measures whether the ground-truth evidence chunk was retrieved in top K. MRR measures how high up the first relevant evidence chunk appears.
* **Common Mistake**: Using simple classification accuracy for a ranking problem.
* **Follow-up**: Why did Recall@5 drop slightly with Cross-Encoder reranking on certain exact keyword queries?

### Q12: How do you handle empty or unsupported retrieval queries?
* **Expected Answer**: The retrieval pipeline validates query inputs, sanitizes special regex characters, checks for empty strings, and returns clean empty list responses with score 0.0 rather than raising unhandled exceptions.
* **Common Mistake**: Allowing downstream components to throw `IndexError` on zero-retrieval results.
* **Follow-up**: How does RAG handle a query where top retrieval scores are below the confidence threshold?

---

## Round 5 — Retrieval Augmented Generation (RAG)

### Q13: How do you enforce answer grounding and prevent LLM hallucinations?
* **Expected Answer**: 1) Strict extractive context constraints; 2) Minimum score thresholds ($\tau=0.25$) triggering explicit abstention (`"INSUFFICIENT_EVIDENCE"`); 3) Exact passage character offset and chunk ID tracking for every cited statement.
* **Common Mistake**: Relying solely on prompt instructions without algorithmic confidence thresholds.
* **Follow-up**: How did you test hallucination mitigation?

### Q14: How are citations generated and verified in your system?
* **Expected Answer**: Every chunk carries metadata (`document_id`, `chunk_id`, `start_char`, `end_char`). During answer generation, extracted text spans are mapped directly back to their source chunk metadata, creating verifiable citation tuples.
* **Common Mistake**: Generating citations as unverified text strings from the LLM prompt.
* **Follow-up**: What happens if a document is deleted after an answer is cached?

### Q15: What is the latency breakdown of your RAG pipeline?
* **Expected Answer**: Hybrid retrieval (~11 ms) + Cross-Encoder reranking (~395 ms) + Extractive QA / evidence generation (~89 ms) = Total RAG response time ~495-520 ms on 4-core CPU.
* **Common Mistake**: Not knowing which stage consumes the majority of runtime latency.
* **Follow-up**: How would you reduce this latency for a real-time web UI?

---

## Round 6 — Machine Learning & Evaluation

### Q16: Walk me through your Phase 9 evaluation methodology.
* **Expected Answer**: Created a 102-query benchmark across 10 query categories (Exact Keyword, Semantic, Numerical, Date, Policy, Contradiction, Negative/Unsupported, etc.). Programmatically executed FAISS, BM25, Hybrid, and Hybrid+Reranker models against ground-truth labels to calculate exact metrics (Recall, Precision, MRR, nDCG, latency percentiles).
* **Common Mistake**: Claiming performance based on 5 manual sample queries.
* **Follow-up**: How were ground-truth relevance labels created?

### Q17: What was the main takeaway from your reranker ablation study?
* **Expected Answer**: Cross-Encoder reranking improved Recall@5 (20.1% vs 17.9%) and nDCG@5 (0.231 vs 0.222), but introduced a ~395 ms CPU latency penalty. For latency-critical applications, pure hybrid RRF is optimal; for accuracy-critical compliance audits, reranking is worth the latency.
* **Common Mistake**: Claiming reranking is always superior in all dimensions.
* **Follow-up**: How would GPU acceleration change this trade-off?

### Q18: How do you detect and evaluate contradiction detection rules?
* **Expected Answer**: Multi-strategy pattern matching (numerical threshold comparison, date interval overlap, retention window conflicts, modal verb negation). Evaluated using Precision, Recall, and F1 score against a labeled benchmark of contradictory vs non-contradictory document pairs.
* **Common Mistake**: Assuming semantic similarity alone indicates contradiction.
* **Follow-up**: Why does high semantic similarity often co-occur with logical contradiction?

---

## Round 7 — Backend Engineering

### Q19: Why did you choose FastAPI over Flask or Django?
* **Expected Answer**: Automatic OpenAPI/Swagger documentation generation, native `pydantic` request/response validation, asynchronous non-blocking event loop capabilities, and high performance benchmarking close to Node.js/Go.
* **Common Mistake**: Saying "because FastAPI is modern" without mentioning Pydantic, ASGI, or Async support.
* **Follow-up**: How do Pydantic schemas enforce type safety across your API endpoints?

### Q20: How is database persistence managed in your system?
* **Expected Answer**: SQLAlchemy ORM backed by SQLite (with path configured via environment variables). Schema includes `documents`, `chunks`, `compliance_rules`, `compliance_findings`, `contradictions`, `risk_scores`, and `audit_logs`.
* **Common Mistake**: Storing raw unindexed JSON blobs without schema relationships.
* **Follow-up**: How would you execute zero-downtime schema migrations when transitioning to PostgreSQL?

### Q21: How is telemetry and observability implemented?
* **Expected Answer**: Prometheus metrics client exposing custom counters and histograms (`query_latency_seconds`, `ingestion_total`, `active_requests`, `error_rate`). Structured JSON logging capturing request IDs across all log messages.
* **Common Mistake**: Relying on basic `print()` statements for production monitoring.
* **Follow-up**: How do request IDs trace a query from Streamlit UI down to SQLite database queries?

---

## Round 8 — System Design

### Q22: How would you scale this system from 1,000 to 1,000,000 documents?
* **Expected Answer**: 1) Replace SQLite with PostgreSQL (pgvector) or dedicated Qdrant/Milvus cluster; 2) Replace single-node BM25 with Elasticsearch / OpenSearch cluster; 3) Decouple document ingestion worker nodes via Celery/RabbitMQ; 4) Move Cross-Encoder inference to dedicated GPU worker pools behind Triton Inference Server.
* **Common Mistake**: Claiming the current single-instance SQLite architecture can handle 1M documents without modification.
* **Follow-up**: How would you shard vector indexes across multiple nodes?

### Q23: How would you handle multi-tenancy and data isolation?
* **Expected Answer**: Logical isolation via `tenant_id` foreign keys indexed across all database tables and vector metadata filters, OR physical isolation via separate database schemas / vector namespaces per enterprise client. Strict RBAC enforcement at API gateway.
* **Common Mistake**: Forgetting to apply tenant filters to FAISS vector search queries.
* **Follow-up**: What is the risk of metadata-based multi-tenant filtering in vector databases?

### Q24: How would you design a zero-downtime index rebuild strategy?
* **Expected Answer**: Blue/Green index swapping. Build index `V_next` in background while `V_current` serves live traffic. Once `V_next` is fully validated, atomically swap active pointer in Redis / API state. Drop `V_current`.
* **Common Mistake**: Clearing live index before re-building, causing downtime.
* **Follow-up**: What happens if document ingestion fails halfway through background indexing?

---

## Round 9 — Security & Reliability

### Q25: How does your system protect against Path Traversal vulnerabilities during document upload?
* **Expected Answer**: Filenames are sanitized via `os.path.basename()`, stripped of null bytes and `../` sequences, saved under deterministic UUIDs, and verified using `os.path.commonpath()` to ensure target paths remain strictly inside the configured upload directory.
* **Common Mistake**: Trusting user-supplied `filename` headers directly in `open(path, 'wb')`.
* **Follow-up**: How do you handle malicious PDF files containing embedded scripts or zip bombs?

### Q26: How do you prevent sensitive information or API keys from leaking into logs?
* **Expected Answer**: Custom log sanitization filters scrub authorization headers, `X-API-Key` values, and bearer tokens before log formatting. Environment variables (`.env`) are excluded from version control via `.gitignore`.
* **Common Mistake**: Printing raw request headers or full request payloads during debug logging.
* **Follow-up**: How did you test secret redaction in automated unit tests?

### Q27: How does your system handle failure injection (e.g., missing index, database restart)?
* **Expected Answer**: Explicit exception handlers catch `FileNotFoundError`, `OperationalError`, and `ModelUnavailableError`, returning structured HTTP 500 JSON responses with safe error messages and request IDs while keeping the main process alive. Recovery utility scripts regenerate BM25 and FAISS indexes automatically upon startup if missing.
* **Common Mistake**: Allowing raw tracebacks to bubble up to the client response.
* **Follow-up**: What is covered in `tests/test_failure_injection.py`?

---

## Round 10 — Project Defense

### Q28: Why is your retrieval benchmark Recall@5 (~20.1%) lower than commercial search engines?
* **Expected Answer**: Commercial benchmarks often evaluate simple web queries with single relevant documents. Our 102-query benchmark evaluates complex multi-document compliance policies where relevant evidence is highly specific, granular, and challenging across 10 specialized categories (e.g., date conflicts, unsupported queries). The benchmark represents realistic zero-shot performance without artificial overfitting.
* **Common Mistake**: Apologizing for metric values or fabricating higher numbers.
* **Follow-up**: What steps would you take to boost Recall@5 to >80%?

### Q29: Can your contradiction detection engine guarantee 0% false positives?
* **Expected Answer**: No rule-based or ML contradiction detector can guarantee 0% false positives due to contextual nuances and domain-specific exceptions. Our system categorizes findings into `CONFIRMED`, `POTENTIAL`, and `DISMISSED`, serving as an auditor copilot to accelerate human review rather than an autonomous decision maker.
* **Common Mistake**: Claiming 100% deterministic perfection in NLP tasks.
* **Follow-up**: How does human feedback loop into your system to dismiss false positives?

### Q30: If you had 6 months and a $50,000 budget, what would you rebuild?
* **Expected Answer**: 1) Migrate to distributed Qdrant + Elasticsearch infrastructure; 2) Train fine-tuned domain-specific Cross-Encoder rerankers on legal/financial text pairs; 3) Implement GPU-accelerated inference pipelines; 4) Add asynchronous document pipeline monitoring with Celery/Redis; 5) Build human-in-the-loop review UI for compliance risk sign-offs.
* **Common Mistake**: Saying "the project is already complete and doesn't need anything."
* **Follow-up**: How would you measure ROI on that $50,000 investment?
