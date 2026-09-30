# Evaluation Methodology

## 1. Metrics Definitions

### Recall@K
$$\text{Recall@K} = \frac{|\text{Retrieved@K} \cap \text{Relevant}|}{|\text{Relevant}|}$$

### Precision@K
$$\text{Precision@K} = \frac{|\text{Retrieved@K} \cap \text{Relevant}|}{K}$$

### Mean Reciprocal Rank (MRR)
$$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

### Normalized Discounted Cumulative Gain (nDCG@K)
$$\text{DCG@K} = \sum_{i=1}^K \frac{\text{rel}_i}{\log_2(i+1)}, \quad \text{nDCG@K} = \frac{\text{DCG@K}}{\text{iDCG@K}}$$

## 2. Benchmark Execution
Run the automated evaluator via:
```powershell
python scripts/run_phase9_evaluation.py
```
All outputs are saved as JSON and CSV files in `reports/phase9/`.
