# System Reliability & Resilience Architecture

## 1. Governance & Threat Mitigations
1. **API Key Authentication**: Constant-time `hmac.compare_digest` verification prevents timing attacks on `AUDITOR_API_KEY`.
2. **Path Traversal Protection**: [`app/core/security.py`](file:///c:/Users/vvsk_/OneDrive/Desktop/Projects/NLP_RAG/enterprise-compliance-auditor/app/core/security.py) extracts base filenames and strips traversal sequences (`../../etc/passwd`, `..\..\Windows\System32\cmd.exe`).
3. **Audit Log Privacy Redaction**: Automatically redacts passwords, API keys, and sensitive tokens prior to SQLite database writes.
4. **Rate Limiting**: Sliding-window counter limits client request bursts to protect CPU search endpoints.

## 2. Fault Recovery Procedures
- **Index Rebuild**: Reconstructs FAISS vector store and BM25 inverted index directly from SQLite database chunk records via `indexing_service.rebuild_index(db)`.
- **Extractive Abstention**: Returns `INSUFFICIENT_EVIDENCE` response when search candidate relevance scores fall below configured thresholds.
