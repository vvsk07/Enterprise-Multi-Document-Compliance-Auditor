# Explainable Risk Scoring Methodology

## Overview

The **Enterprise-Grade Multi-Document Intelligence & Compliance Auditor** uses a multi-component, deterministic risk-scoring formula to evaluate document-level and portfolio-level operational and legal compliance risk.

Unlike opaque black-box machine learning scores, every risk assessment produced by this platform is **100% explainable and traceable** to specific compliance rule failures, factual contradictions, severity weights, and evidence spans.

---

## 1. Document Risk Score Formula

The document risk score ($R_{\text{doc}} \in [0.0, 100.0]$) is calculated as a weighted sum of four component metrics:

$$R_{\text{doc}} = \min\left(100.0, \max\left(0.0, w_{\text{comp}} S_{\text{comp}} + w_{\text{contra}} S_{\text{contra}} + w_{\text{sev}} S_{\text{sev}} + w_{\text{rev}} S_{\text{rev}}\right)\right)$$

### Default Weights (Configurable in `configs/settings.yaml`):

| Component | Variable | Default Weight | Description |
| :--- | :--- | :--- | :--- |
| **Compliance Risk** | $S_{\text{comp}}$ | **45%** ($0.45$) | Ratio and severity of failed compliance rules against applicable rules. |
| **Contradiction Risk** | $S_{\text{contra}}$ | **30%** ($0.30$) | Scaled presence of cross-document factual contradictions. |
| **Severity Risk** | $S_{\text{sev}}$ | **15%** ($0.15$) | Density of HIGH severity findings across compliance and contradictions. |
| **Review / Uncertainty** | $S_{\text{rev}}$ | **10%** ($0.10$) | Pending manual review items (`NEEDS_REVIEW`, `POTENTIAL`). |

---

## 2. Component Calculations

### A. Compliance Risk ($S_{\text{comp}}$)
Calculated against applicable rules ($\text{PASS} + \text{FAIL} + \text{NEEDS\_REVIEW}$):
- `NOT_APPLICABLE` rules are excluded so non-relevant rules do not dilute or inflate document risk.
- Points allocated:
  - $\text{HIGH Fail} = 100.0$
  - $\text{MEDIUM Fail} = 60.0$
  - $\text{LOW Fail} = 30.0$
  - $\text{NEEDS\_REVIEW} = 30.0$

$$S_{\text{comp}} = \min\left(100.0, \frac{100 \cdot N_{\text{high\_fail}} + 60 \cdot N_{\text{med\_fail}} + 30 \cdot N_{\text{low\_fail}} + 30 \cdot N_{\text{review}}}{N_{\text{applicable}}}\right)$$

### B. Contradiction Risk ($S_{\text{contra}}$)
Calculated from active cross-document findings involving the document:
- Status Multipliers: `CONFIRMED` $= 1.0$, `POTENTIAL` $= 0.5$, `REVIEWED` $= 0.25$, `DISMISSED` $= 0.0$.
- Severity Multipliers: `HIGH` $= 1.0$, `MEDIUM` $= 0.6$, `LOW` $= 0.3$.

$$S_{\text{contra}} = \min\left(100.0, \sum_{c \in \text{Contradictions}} 35.0 \times M_{\text{status}}(c) \times M_{\text{sev}}(c) \times \text{Confidence}(c)\right)$$

### C. Severity Risk ($S_{\text{sev}}$)
$$S_{\text{sev}} = \min\left(100.0, 40.0 \cdot N_{\text{high\_total}} + 20.0 \cdot N_{\text{med\_total}}\right)$$

### D. Review / Uncertainty Risk ($S_{\text{rev}}$)
$$S_{\text{rev}} = \min\left(100.0, 25.0 \cdot N_{\text{needs\_review}} + 25.0 \cdot N_{\text{potential\_contradictions}}\right)$$

---

## 3. Risk Level Mapping

| Score Range | Risk Level | Operational Action |
| :--- | :--- | :--- |
| **0.00 – 24.99** | `LOW` 🟢 | Compliant; standard archiving. |
| **25.00 – 49.99** | `MEDIUM` 🟠 | Moderate issues; review non-critical items. |
| **50.00 – 74.99** | `HIGH` 🔴 | Mandatory legal & compliance remediation required. |
| **75.00 – 100.0** | `CRITICAL` 🚨 | Escalated audit priority; blocking execution. |

---

## 4. Portfolio Aggregation

Portfolio-level risk is calculated as a weighted average over all active portfolio documents weighted by applicable compliance rules, ensuring documents with zero applicable rules do not skew executive reporting metrics:

$$R_{\text{portfolio}} = \frac{\sum_{d} w_d R_{\text{doc}}(d)}{\sum_{d} w_d}, \quad \text{where } w_d = \max(1, N_{\text{applicable}}(d))$$
