# LinkedIn Project Announcement

## Post Title: Launching Enterprise-Grade Multi-Document Intelligence & Compliance Auditor 🚀

---

### Post Text

I’m excited to share my latest project: **Enterprise-Grade Multi-Document Intelligence & Compliance Auditor** — an end-to-end NLP & Information Retrieval system designed to solve complex policy verification, cross-document contradiction detection, and risk scoring across enterprise document collections.

### 💡 The Problem
In financial, legal, and compliance workflows, analyzing hundreds of policy documents, vendor contracts, and security guidelines manually leads to overlooked contradictions, missed non-compliance items, and high operational costs. Standard keyword search misses contextual semantics, while pure vector search often misses exact numerical/code identifiers.

### 🛠️ What I Built
I engineered a modular, production-ready system featuring:
* **Hybrid Lexical + Dense Retrieval**: Combines BM25 (exact keyword match) and FAISS + SentenceTransformers (`all-MiniLM-L6-v2`) via Reciprocal Rank Fusion (RRF).
* **Cross-Encoder Reranking**: Uses `ms-marco-MiniLM-L-6-v2` for precise passage scoring.
* **Grounded Advanced RAG**: Extractive QA with strict evidence attribution and explicit abstention triggers to prevent hallucination.
* **Compliance & Contradiction Engines**: Automated rule evaluation (Pass/Fail/Review) and multi-strategy cross-document contradiction detection (numeric, date, retention, payment, negation).
* **Risk Analytics & Enterprise Security**: Weighted risk scoring, RBAC API Key authentication, strict path traversal defenses, audit logging, Prometheus metrics, and a Streamlit interactive dashboard.

### 📊 Empirical Evaluation (Phase 9 Benchmark)
* Tested on a **102-query benchmark dataset** across 10 distinct categories.
* **Reranking Impact**: Hybrid + Cross-Encoder achieved **20.1% Recall@5** (compared to 17.9% for raw hybrid).
* **Latency Profile**: Sub-15ms hybrid retrieval latency on CPU, with end-to-end RAG QA executed in ~495ms.
* **Regression Testing**: **91/91 automated tests passing** across unit, integration, failure injection, and recovery test suites.

### 🧰 Tech Stack
`Python` | `FastAPI` | `Streamlit` | `FAISS` | `SentenceTransformers` | `BM25` | `SQLAlchemy` | `SQLite` | `ReportLab` | `Prometheus` | `Docker` | `Pytest`

📁 **GitHub Repository**: [Enterprise Compliance Auditor](https://github.com/your-username/enterprise-compliance-auditor)
📄 **Research Paper & Benchmark Methodology**: Included in `/research/paper/`

#MachineLearning #NLP #InformationRetrieval #RAG #AI #Python #FastAPI #FAISS #VectorSearch #Compliance #SystemDesign
