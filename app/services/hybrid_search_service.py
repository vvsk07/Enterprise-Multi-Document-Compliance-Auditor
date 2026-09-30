"""
Hybrid Search Service (BM25 Lexical + FAISS Semantic Candidate Fusion).
Normalizes raw retrieval scores and computes a weighted hybrid relevance score.
"""

from typing import List, Dict, Any, Optional
from app.services.vector_store import vector_store
from app.services.bm25_service import bm25_service
from app.services.embedding_service import embedding_service
from app.config import get_retrieval_config
from app.core.logging import logger

class HybridSearchService:
    def __init__(self):
        cfg = get_retrieval_config()
        self.bm25_weight = cfg.get("bm25_weight", 0.40)
        self.dense_weight = cfg.get("dense_weight", 0.60)
        self.candidate_k = cfg.get("candidate_k", 20)
        self.final_k = cfg.get("final_k", 5)

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        bm25_weight: Optional[float] = None,
        dense_weight: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval combining BM25 lexical and FAISS semantic candidates with min-max normalization.
        """
        if not query or not query.strip():
            return []

        k_candidates = top_k if top_k is not None else self.candidate_k

        w_bm25 = bm25_weight if bm25_weight is not None else self.bm25_weight
        w_dense = dense_weight if dense_weight is not None else self.dense_weight

        # Normalize weights to sum to 1.0
        total_w = w_bm25 + w_dense
        if total_w > 0:
            w_bm25 /= total_w
            w_dense /= total_w
        else:
            w_bm25, w_dense = 0.5, 0.5

        # 1. Lexical retrieval via BM25
        bm25_results = bm25_service.search(query, top_k=k_candidates, filters=filters)

        # 2. Semantic retrieval via FAISS
        query_vector = embedding_service.embed_single(query)
        dense_results = vector_store.similarity_search(query_vector, top_k=k_candidates, filters=filters)

        # Normalize BM25 scores (min-max or max scaling)
        bm25_scores = [r["score"] for r in bm25_results]
        max_bm25 = max(bm25_scores) if bm25_scores else 1.0
        min_bm25 = min(bm25_scores) if bm25_scores else 0.0
        range_bm25 = (max_bm25 - min_bm25) if (max_bm25 - min_bm25) > 1e-6 else 1.0

        # Normalize FAISS scores (cosine similarity range [0, 1])
        # FAISS IP vectors are normalized, so score is cosine similarity in [-1, 1]
        
        candidates_map: Dict[str, Dict[str, Any]] = {}

        # Process BM25 candidates
        for r in bm25_results:
            cid = r["chunk_id"]
            raw_bm25 = r["score"]
            norm_bm25 = (raw_bm25 - min_bm25) / range_bm25 if max_bm25 > min_bm25 else (1.0 if raw_bm25 > 0 else 0.0)
            
            candidates_map[cid] = {
                **r,
                "raw_bm25": round(raw_bm25, 4),
                "norm_bm25": round(norm_bm25, 4),
                "raw_dense": 0.0,
                "norm_dense": 0.0,
            }

        # Process FAISS candidates
        for r in dense_results:
            cid = r["chunk_id"]
            raw_dense = r["score"]
            norm_dense = max(0.0, min(1.0, float(raw_dense)))

            if cid in candidates_map:
                candidates_map[cid]["raw_dense"] = round(raw_dense, 4)
                candidates_map[cid]["norm_dense"] = round(norm_dense, 4)
            else:
                candidates_map[cid] = {
                    **r,
                    "raw_bm25": 0.0,
                    "norm_bm25": 0.0,
                    "raw_dense": round(raw_dense, 4),
                    "norm_dense": round(norm_dense, 4),
                }

        # Calculate hybrid score
        fused_results = []
        for cid, item in candidates_map.items():
            hybrid_score = (w_bm25 * item["norm_bm25"]) + (w_dense * item["norm_dense"])
            item["score"] = round(hybrid_score, 4)
            item["hybrid_score"] = round(hybrid_score, 4)
            fused_results.append(item)

        # Rank candidates by hybrid score descending
        fused_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        logger.info(
            f"Hybrid search query='{query[:30]}...' -> BM25: {len(bm25_results)}, FAISS: {len(dense_results)}, Fused: {len(fused_results)}"
        )
        return fused_results[:k_candidates]

hybrid_search_service = HybridSearchService()
