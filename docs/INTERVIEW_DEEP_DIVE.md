# System Deep-Dive & Algorithmic Explanations

This document provides intuitive, mathematically sound explanations of the key algorithmic and architectural decisions made in the **Enterprise-Grade Multi-Document Intelligence & Compliance Auditor**.

---

## 1. BM25 (Lexical Information Retrieval)

### What is it?
BM25 (Best Matching 25) is a probabilistic bag-of-words retrieval function that rates candidate document passages based on the occurrences of query terms, adjusted for document length and term frequency saturation.

$$\text{BM25}(D, Q) = \sum_{i=1}^{n} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$

### Why is it used?
Dense vector representations often lose precise lexical matching for specific keywords, numerical thresholds, section IDs (e.g., `ISO 27001 Section 5.2`), or technical acronyms. BM25 ensures exact-match recall for domain-specific terminology.

---

## 2. FAISS & Vector Embeddings

### What is FAISS?
FAISS (Facebook AI Similarity Search) is a high-performance library for efficient similarity search and clustering of dense vectors. In our system, we utilize `faiss.IndexFlatIP` (Inner Product) paired with L2-normalized embeddings, equivalent to Cosine Similarity.

### What are Embeddings?
Vector embeddings (generated via `sentence-transformers/all-MiniLM-L6-v2`) map semantic text into a continuous 384-dimensional vector space. Passages with similar conceptual meaning (e.g., "data safety" and "information security") are positioned close together in vector space regardless of exact term overlap.

---

## 3. Hybrid Fusion & Reciprocal Rank Fusion (RRF)

### Why Hybrid Retrieval?
BM25 excels at exact keyword matching but fails on synonyms or paraphrasing. Dense FAISS search excels at semantic capture but degrades on arbitrary codes or exact numbers. Combining both yields robust retrieval across diverse query types.

### How does RRF work?
Reciprocal Rank Fusion merges two distinct ranked lists without requiring raw score normalization:

$$RRF\_Score(d \in D) = \frac{1}{k + r_{\text{BM25}}(d)} + \frac{1}{k + r_{\text{FAISS}}(d)}$$

Where $k=60$ is a smoothing constant. Passages ranking near the top in both lists receive exponentially higher fused scores.

---

## 4. Cross-Encoder Reranking

### Dual-Encoder vs. Cross-Encoder
* **Bi-Encoder (FAISS)**: Encodes Query and Document *independently* into dense vectors. Fast cosine distance calculation, but misses fine-grained token-level cross-attention.
* **Cross-Encoder**: Feeds the concatenated pair `(Query, Passage)` simultaneously into transformer self-attention layers (`cross-encoder/ms-marco-MiniLM-L-6-v2`).

### Trade-Off
* **Quality**: Substantially higher ranking precision because every query token attends to every passage token.
* **Latency**: Slower CPU computation (~20-40 ms per batch of candidate passages vs ~0.1 ms for FAISS).

---

## 5. Grounded RAG & Evidence Extraction

### Architecture
Retrieval Augmented Generation (RAG) feeds top-$K$ reranked passages into an extractive QA module.

```text
Query + Top-K Passages ──> Extractive RAG ──> Answer + Grounded Citations (DocID, ChunkID)
```

### Prevention of Hallucination
* **Abstention Threshold**: If maximum passage relevance score is below $\tau=0.25$, the system explicitly returns `"INSUFFICIENT_EVIDENCE"` rather than generating speculative answers.
* **Citation Traceability**: Every extracted answer fragment is mapped back to exact `document_id`, `chunk_id`, and character offsets.

---

## 6. Document Chunking Strategy

### Why Chunk?
Large documents exceed LLM context windows and dilute vector embedding precision.

### Implemented Strategy
* **Chunk Size**: 512 characters.
* **Overlap**: 50 characters (preserves sentence context across boundaries).
* **Metadata Attachment**: Each chunk inherits document-level metadata (`document_id`, `domain`, `document_type`, `date`).

---

## 7. Cross-Document Contradiction Detection

### Algorithmic Pipeline
1. **Candidate Pair Mining**: Extracts passage pairs across distinct documents sharing high semantic relevance or overlapping entities.
2. **Deterministic Rule Extraction**:
   * **Numeric**: Detects conflicting quantitative values (e.g., 30 days vs. 90 days).
   * **Date/Duration**: Detects conflicting dates or operational windows.
   * **Negation**: Identifies opposing modal verbs (e.g., "shall retain" vs. "shall not retain").
3. **Confidence Scoring**: Combines rule match confidence with semantic similarity weights.
4. **Classification**: Categorizes findings into `CONFIRMED`, `POTENTIAL`, or `DISMISSED`.

---

## 8. Configurable Compliance Engine

### Mechanics
Evaluates document chunks against structured JSON/YAML compliance rules.

```json
{
  "rule_id": "COMP-001",
  "category": "Data Security",
  "required_keywords": ["encryption", "AES-256"],
  "min_passages": 1
}
```

### Severity & Status
* **PASS**: Rule requirements satisfied with verified citations.
* **FAIL**: Explicit violation found or required standard absent.
* **REVIEW**: Partial evidence requiring human oversight.

---

## 9. Risk Scoring Methodology

### Formula
$$R_{\text{doc}} = w_1 \cdot (100 - S_{\text{compliance}}) + w_2 \cdot (N_{\text{contradictions}} \times 15) + w_3 \cdot S_{\text{critical\_gaps}}$$

### Risk Categories
* `0.0 - 25.0`: **LOW**
* `25.1 - 50.0`: **MEDIUM**
* `50.1 - 75.0`: **HIGH**
* `75.1 - 100.0`: **CRITICAL**

---

## 10. API Security & Enterprise Audit Logging

### API Key Authentication & Rate Limiting
* Header-based `X-API-Key` validation linked to Role-Based Access Control (RBAC).
* Token-bucket rate limiting (60 requests/minute per client).

### Path Traversal Defense
* Sanitizes document filenames via `os.path.basename()` and enforces strict canonical root verification (`os.path.commonpath`).

### Immutable Audit Log
* Logs all operations (ingestion, query, compliance check, risk evaluation) into SQLite with timestamp, user context, client IP, action type, and hash signatures.
