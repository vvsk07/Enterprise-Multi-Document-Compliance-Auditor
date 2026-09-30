# Experimental Results & Benchmarks

## 1. Retrieval & Reranker Ablation (102 Benchmark Queries)
| System | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | P@5 | Avg ms | P50 ms | P95 ms | P99 ms |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FAISS Only** | 13.0% | 16.8% | 19.6% | 25.0% | 0.168 | 0.245 | 0.074 | 11.4 ms | 10.8 ms | 13.7 ms | 16.8 ms |
| **BM25 Only** | 7.6% | 14.1% | 15.8% | 21.7% | 0.118 | 0.183 | 0.061 | 0.2 ms | 0.2 ms | 0.3 ms | 0.4 ms |
| **Hybrid (0.4/0.6)** | 10.9% | 14.7% | 17.9% | 22.8% | 0.148 | 0.222 | 0.070 | 11.1 ms | 11.1 ms | 12.9 ms | 14.8 ms |
| **Hybrid + Reranker** | **8.2%** | **19.0%** | **20.1%** | **22.8%** | **0.144** | **0.231** | **0.078** | **442.8 ms** | **381.7 ms** | **469.1 ms** | **511.2 ms** |

## 2. Full System Latency Percentiles
| Operation | Average (ms) | P50 Median (ms) | P90 (ms) | P95 (ms) | P99 Tail (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **FAISS Search** | 10.3 ms | 10.6 ms | 11.6 ms | 11.6 ms | 11.6 ms |
| **BM25 Search** | 0.1 ms | 0.1 ms | 0.2 ms | 0.2 ms | 0.2 ms |
| **Hybrid Search** | 12.3 ms | 12.1 ms | 16.8 ms | 16.8 ms | 16.8 ms |
| **Cross-Encoder Rerank** | 21.9 ms | 21.9 ms | 25.6 ms | 25.6 ms | 25.6 ms |
| **Advanced RAG Pipeline** | 486.3 ms | 495.7 ms | 511.4 ms | 511.4 ms | 511.4 ms |
| **Compliance Audit** | 620.7 ms | 620.9 ms | 719.8 ms | 719.8 ms | 719.8 ms |
| **Contradiction Detection** | 491.3 ms | 497.1 ms | 539.9 ms | 539.9 ms | 539.9 ms |
| **Risk Calculation** | 17.7 ms | 17.2 ms | 25.5 ms | 25.5 ms | 25.5 ms |

## 3. Synthetic Chunk Scalability (BM25 Indexing)
| Chunks | Build Time (ms) | Search Latency (ms) | Estimated Memory (KB) |
| :---: | :---: | :---: | :---: |
| 100 | 2.1 ms | 0.05 ms | 45.0 KB |
| 500 | 12.5 ms | 0.12 ms | 225.0 KB |
| 1,000 | 28.4 ms | 0.24 ms | 450.0 KB |
| 5,000 | 145.1 ms | 1.15 ms | 2,250.0 KB |
