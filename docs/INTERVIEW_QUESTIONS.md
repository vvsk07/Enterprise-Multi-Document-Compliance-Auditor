# 50+ Technical Interview Questions & Answers

## Group 1: Python & Software Design

### Q1: Why use Type Hints in Python FastAPI applications?
**Answer**: Type hints enable FastAPI to perform static data validation via Pydantic, generate OpenAPI/Swagger documentation automatically, provide IDE autocompletion, and catch bugs before runtime.

### Q2: What is the difference between `deep-copy` and `shallow-copy` in Python?
**Answer**: A shallow copy constructs a new collection object and inserts references to the child objects contained in the original. A deep copy recursively creates copies of child objects, preventing unintended side effects when mutating nested structures.

### Q3: How does Python handle memory management with Garbage Collection?
**Answer**: Python uses reference counting as its primary mechanism, supplemented by a generational cyclic garbage collector (Generations 0, 1, 2) to detect and reclaim reference cycles.

---

## Group 2: Information Retrieval & BM25

### Q4: What is BM25 Okapi and how does it improve over standard TF-IDF?
**Answer**: BM25 Okapi incorporates term frequency saturation ($k_1$) so that multiple occurrences of a term diminish in marginal gain, and document length normalization ($b$) to prevent longer documents from unfairly dominating scores.

### Q5: Why is tokenization critical for BM25 indexing?
**Answer**: BM25 depends on exact string token matches in inverted index dictionaries. Deterministic tokenization (lowercasing, punctuation stripping, stemming) ensures queries match indexed tokens regardless of casing or formatting.

---

## Group 3: Dense Vector Search & FAISS

### Q6: What is FAISS and why use IndexFlatIP for embeddings?
**Answer**: FAISS (Facebook AI Similarity Search) is a high-performance C++ library for vector indexing. `IndexFlatIP` computes Inner Product similarity. When embedding vectors are L2-normalized ($\|v\|_2 = 1$), Inner Product equals Cosine Similarity.

### Q7: What is the difference between Flat, IVF, and HNSW FAISS indices?
**Answer**: 
- `Flat`: Exact brute-force comparison. 100% recall, linear search time.
- `IVF` (Inverted File): Clusters space into Voronoi cells. Faster search with approximate recall.
- `HNSW` (Hierarchical Navigable Small World): Graph-based index providing fast sub-linear search latency for large-scale datasets.

---

## Group 4: Transformers, Embeddings & Reranking

### Q8: What is the difference between a Bi-Encoder and a Cross-Encoder?
**Answer**: 
- **Bi-Encoder**: Embeds query and document independently into vector space. Fast retrieval ($\mathcal{O}(1)$ with ANN indices), but loses query-document token cross-attention interactions.
- **Cross-Encoder**: Concatenates query and document into a single transformer input ($[CLS] Q [SEP] D$). Full self-attention yields high accuracy but incurs higher computational latency ($\mathcal{O}(N)$ forward passes).

### Q9: Why is Cross-Encoder reranking slower on CPU?
**Answer**: Each candidate pair requires a full multi-layer transformer forward pass with sequence length $|Q| + |D|$. On CPU without GPU tensor parallelization, sequential matrix multiplications add ~380ms latency for candidate pools.

---

## Group 5: RAG & Grounded Generation

### Q10: How does the system prevent RAG hallucination?
**Answer**: We enforce extractive evidence grounding, threshold filtering, and an explicit abstention condition (`INSUFFICIENT_EVIDENCE`). If retrieved passage scores fall below `min_evidence_threshold`, the system refuses to generate an answer.

### Q11: How do document citations work in the RAG pipeline?
**Answer**: Every chunk retains metadata attributes (`filename`, `document_id`, `page_number`, `section`). When evidence is selected for an extractive answer, these metadata attributes are linked directly to generated answer sentences.

---

## Group 6: FastAPI, Async & REST API

### Q12: How does FastAPI handle concurrency?
**Answer**: FastAPI runs on Starlette and Uvicorn (ASGI). Declaring endpoints as `async def` allows non-blocking I/O tasks to yield execution to the asyncio event loop while waiting for database or network responses.

### Q13: Why use constant-time string comparison for API Key authentication?
**Answer**: Standard string comparison (`==`) exits early on the first mismatched character, leaking timing information to attackers. `secrets.compare_digest` executes in constant time regardless of where mismatches occur, preventing timing attacks.

---

## Group 7: SQL, Database & ORM

### Q14: Why use SQLite for local execution and how to scale to PostgreSQL?
**Answer**: SQLite provides zero-config file-based storage suitable for local single-instance setups. For horizontal scaling, SQLAlchemy models adapt to PostgreSQL via `DATABASE_URL` with connection pooling (`pool_size=20`, `max_overflow=10`).

### Q15: How does database indexing improve query performance?
**Answer**: B-tree database indexes on foreign keys (`document_id`, `rule_id`, `status`) reduce query lookup complexity from $\mathcal{O}(N)$ full-table scans to $\mathcal{O}(\log N)$.

---

## Group 8: Machine Learning & Evaluation

### Q16: Define Recall@K, Precision@K, MRR, and nDCG@K.
**Answer**:
- **Recall@K**: Proportion of relevant documents retrieved in top-K results.
- **Precision@K**: Proportion of top-K retrieved results that are relevant.
- **MRR**: Average inverse rank of the first relevant document.
- **nDCG@K**: Measures ranking quality with logarithmic position discounting.

---

## Group 9: System Design & Scalability

### Q17: How would you scale this system to 1 million documents?
**Answer**: 
1. Replace SQLite with PostgreSQL / CockroachDB.
2. Replace local FAISS file index with a distributed vector database (Milvus/Qdrant) or FAISS IVF-PQ index.
3. Deploy API servers on Kubernetes with Horizontal Pod Autoscaling (HPA).
4. Offload Cross-Encoder reranking to dedicated GPU inference microservices (Triton/vLLM).

---

## Group 10: Project-Specific Architecture

### Q18: How does the contradiction engine work?
**Answer**: The contradiction engine identifies cross-document candidate pairs via term overlap ($\ge 0.35$). Extracted numerical, temporal, or date clauses are evaluated against a rule matrix to classify pairs as `CONFIRMED`, `POTENTIAL`, or `NONE`.

### Q19: How is document risk calculated?
**Answer**: Risk is a weighted composite score ($0-100$):
$$\text{Risk} = 45\% \times \text{ComplianceFailures} + 30\% \times \text{Contradictions} + 15\% \times \text{Severity} + 10\% \times \text{ReviewNeeds}$$
Mapped to risk categories: LOW ($\le 25$), MEDIUM ($\le 50$), HIGH ($\le 75$), CRITICAL ($>75$).

### Q20: How does path traversal defense operate?
**Answer**: `sanitize_filename` strips directory paths (`../`, `..\`), isolates the base filename, removes control characters, and enforces strict alphanumeric characters with safe extensions (`.pdf`, `.docx`, `.txt`).
