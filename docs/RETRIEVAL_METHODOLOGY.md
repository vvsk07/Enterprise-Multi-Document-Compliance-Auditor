# HYBRID RETRIEVAL & ADVANCED RAG METHODOLOGY

## Multi-Stage Retrieval Architecture

1. **Query Analysis**: Deterministically parses user queries for document scope, compliance terms, numerical constraints, and dates.
2. **Lexical Retrieval (BM25)**: Evaluates Okapi BM25 scores over tokenized document chunks to catch exact keyword matches (e.g. "RULE-001", "30 days", "7 years").
3. **Semantic Retrieval (FAISS)**: Computes dense inner-product cosine similarity embeddings (`sentence-transformers/all-MiniLM-L6-v2`).
4. **Candidate Fusion & Normalization**: Scores are normalized using min-max scaling and combined:
   $$\text{Hybrid Score} = w_{\text{bm25}} \cdot \text{Norm}_{\text{bm25}} + w_{\text{dense}} \cdot \text{Norm}_{\text{dense}}$$
   Default weights: $w_{\text{bm25}} = 0.40$, $w_{\text{dense}} = 0.60$.
5. **Cross-Encoder Reranking**: Evaluates query-chunk pairs with `cross-encoder/ms-marco-MiniLM-L-6-v2` on CPU to fine-rank top candidates.
6. **Extractive Grounded RAG**: Synthesizes fact-grounded answers strictly from selected evidence chunks with traceable source citations.
