# Supplementary Methodological Details

## 1. Compliance Rules Definition Schema
The compliance engine reads deterministic and semantic rules structured as:

```json
{
  "rule_id": "RULE-SEC-001",
  "name": "Mandatory Encryption Standard",
  "category": "Security Policy",
  "severity": "HIGH",
  "type": "presence",
  "keywords": ["AES 256", "encryption at rest", "TLS 1.3"],
  "semantic_query": "data protection and encryption standard requirements",
  "enabled": true
}
```

## 2. Contradiction Detection Algorithm
Candidate paired chunks across documents are extracted where term overlap $\ge 0.35$. Extracted numerical or temporal clauses are compared via rule matrix logic:

```python
if numeric_clause_A != numeric_clause_B:
    status = "CONFIRMED" if high_confidence else "POTENTIAL"
```
