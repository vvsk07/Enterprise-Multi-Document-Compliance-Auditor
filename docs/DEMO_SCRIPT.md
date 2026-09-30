# Interactive 5-Minute Project Demo Script

## Overview
This script outlines a 5-minute live demonstration flow for the **Enterprise-Grade Multi-Document Intelligence & Compliance Auditor**.

---

## Step 1: Launch Backend & Dashboard (0:00 - 0:30)
Run in terminal:
```powershell
uvicorn app.main:app --reload --port 8000
streamlit run frontend/streamlit_app.py
```
Open browser to `http://localhost:8501`. Highlight the 15-module sidebar navigation.

---

## Step 2: Ingest & Index Contracts (0:30 - 1:30)
1. Navigate to **Tab 1: Ingestion**.
2. Upload sample PDF/DOCX files (e.g. `consulting_agreement.pdf`, `security_policy.pdf`).
3. Click **Ingest & Chunk**. Point out automatic classification, OCR fallback, SpaCy NLP sentence chunking, and FAISS/BM25 dual indexing.

---

## Step 3: Hybrid Search vs BM25 Demonstration (1:30 - 2:30)
1. Navigate to **Tab 11: Advanced Hybrid Search**.
2. Query: *"What is the required data retention period?"*
3. Compare **BM25 Lexical** vs **FAISS Dense** vs **Hybrid Candidate Fusion**.
4. Show how Hybrid search captures both keyword specificity ("retention period") and semantic intent.

---

## Step 4: Advanced RAG with Citations & Abstention (2:30 - 3:30)
1. Navigate to **Tab 12: Advanced RAG Trace**.
2. Ask: *"What are the vendor breach notification requirements?"*
3. Highlight exact extractive answer, source document citations (`security_policy.pdf`, Page 3), and confidence scores.
4. Ask an out-of-domain query: *"What company aircraft is assigned to site visits?"*
5. Show how the RAG engine abstains with `INSUFFICIENT_EVIDENCE` instead of hallucinating.

---

## Step 5: Compliance Audit & Contradiction Detection (3:30 - 4:30)
1. Navigate to **Tab 6: Compliance Reports**. Show automated rule evaluation across SOC 2, MFA, and data encryption policies.
2. Navigate to **Tab 7: Contradiction Engine**. Show detected cross-document term conflicts (e.g., Net 30 payment terms in Consulting Agreement vs Net 60 in Payment Terms Schedule).

---

## Step 6: Risk Dashboard, Audit Logs & Metrics (4:30 - 5:00)
1. Navigate to **Tab 8: Risk Dashboard**. Point out weighted 0–100 risk scoring.
2. Navigate to **Tab 15: Audit Logs & Performance**. Show secret-redacted audit trails and Prometheus endpoints at `/metrics/prometheus`.
