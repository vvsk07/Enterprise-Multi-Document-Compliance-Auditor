# Evaluation Dataset Guide

## 1. Structure & Schema
The evaluation dataset is stored at `data/evaluation/phase9_benchmark.json`. Each entry follows the canonical schema:

```json
{
  "query_id": "Q001",
  "query": "What is the vendor termination notice requirement?",
  "relevant_document_ids": ["doc_consulting_agreement", "doc_vendor_policy"],
  "relevant_chunk_ids": ["chunk_consulting_term", "chunk_vendor_notice"],
  "category": "Contractual",
  "difficulty": "easy"
}
```

## 2. Query Categories
1. **Exact Keyword**: Direct token matching (e.g. "AES 256-bit encryption").
2. **Semantic Paraphrase**: Conceptual similarity without identical vocabulary (e.g. "Confidential information non-disclosure duration obligations").
3. **Numerical**: Numeric thresholds, day limits, dollar amounts (e.g. "Net 30 days payment deadline").
4. **Date-Related**: Expiration dates, effective dates, survival terms (e.g. "Agreement effective date January 15 2024").
5. **Policy/Compliance**: Security, privacy, BYOD, MFA, and auditing policies (e.g. "SOC 2 Type II audit report submission").
6. **Contractual**: IP ownership, indemnification, liability caps, dispute resolution.
7. **Contradiction**: Inconsistent terms between paired documents (e.g. "30 days notice in NDA vs 60 days in MSA").
8. **Entity-Specific**: Specified courts, jurisdictions, standards.
9. **Multi-Document**: Cross-document term comparisons.
10. **Negative / Unsupported**: Queries with zero evidence in the corpus, testing abstention (`INSUFFICIENT_EVIDENCE`).

## 3. Custom Evaluation Documents
Users can add custom evaluation documents under `data/evaluation/documents/` and append ground-truth query entries to `data/evaluation/phase9_benchmark.json`.
