# Phase 7 — Explainable Compliance & Risk Scoring / Audit Dashboard Technical Documentation

## Overview

Phase 7 transforms the **Enterprise-Grade Multi-Document Intelligence & Compliance Auditor** into a complete enterprise audit intelligence platform.

It combines findings from Phase 3 (NLP Classification & Entities), Phase 4 (Embeddings, FAISS, grounded RAG), Phase 5 (Compliance Rule Engine), and Phase 6 (Cross-Document Contradiction Engine) into a unified, explainable risk score, executive dashboard, and automated PDF/CSV/JSON report exporter.

---

## Technical Architecture

```text
Document Ingestion (PDF / DOCX / TXT)
                  │
                  ▼
TF-IDF Classification + spaCy NER + FAISS Indexing
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
Compliance Engine    Contradiction Engine
(Rules 001 - 010)    (Candidate FAISS search + Facts)
        │                   │
        └─────────┬─────────┘
                  ▼
      Risk Scoring Engine Service
      (Weighted 4-component calculation)
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
    Risk Score Executive  PDF / CSV / JSON
    Breakdown  Dashboard  Report Exporter
```

---

## Key Components Introduced in Phase 7

1. **Database Model (`RiskAssessment`)**:
   - Stores `risk_score`, `risk_level`, component raw and weighted scores, finding counts, JSON risk factors, and JSON actionable recommendations.
2. **Scoring Engine (`RiskScoringService`)**:
   - Computes document-level and portfolio-level risk with transparent component breakdowns (Compliance 45%, Contradictions 30%, Severity 15%, Review 10%).
3. **Recommendation Engine (`RiskRecommendationService`)**:
   - Generates deterministic, evidence-grounded remediation recommendations for every compliance failure and policy contradiction.
4. **Audit Report Service (`AuditReportService`)**:
   - Produces structured JSON packages, CSV datasets (via Pandas), and multi-page formatted PDF reports (via ReportLab).
5. **REST API Endpoints**:
   - `POST /documents/{id}/risk`
   - `GET /documents/{id}/risk`
   - `GET /documents/{id}/risk/breakdown`
   - `POST /risk/recalculate`
   - `GET /risk/overview`
   - `GET /risk/high-risk-documents`
   - `GET /risk/recommendations`
   - `GET /reports/audit/json`
   - `GET /reports/audit/csv`
   - `GET /reports/audit/pdf`
6. **Streamlit Executive Dashboard (`tab10`)**:
   - Displays portfolio KPI cards, risk distribution charts, document inspector, risk factor explanations, and one-click PDF/CSV/JSON download buttons.
