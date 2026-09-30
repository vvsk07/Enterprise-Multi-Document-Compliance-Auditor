"""
Cross-Encoder Reranker Service.
Uses HuggingFace CrossEncoder (e.g., cross-encoder/ms-marco-MiniLM-L-6-v2) for fine-grained re-ranking of retrieved candidates.
Includes graceful fallback if reranker model loading or inference is unavailable.
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import CrossEncoder

from app.config import get_reranker_config
from app.core.logging import logger

class RerankerService:
    def __init__(self):
        cfg = get_reranker_config()
        self.enabled = cfg.get("enabled", True)
        self.model_name = cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.batch_size = cfg.get("batch_size", 8)
        self.final_k = cfg.get("final_k", 5)
        self._model: Optional[CrossEncoder] = None
        self._is_available = True

    def _get_model(self) -> Optional[CrossEncoder]:
        if not self.enabled or not self._is_available:
            return None

        if self._model is None:
            try:
                logger.info(f"Loading CrossEncoder model '{self.model_name}' on CPU...")
                self._model = CrossEncoder(self.model_name, max_length=512)
                logger.info(f"Successfully loaded CrossEncoder model '{self.model_name}'.")
            except Exception as e:
                logger.warning(f"Failed to load CrossEncoder model '{self.model_name}': {e}. Falling back to hybrid ranking.")
                self._is_available = False
                self._model = None

        return self._model

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Reranks candidate chunk dicts using CrossEncoder relevance scores.
        If reranker is disabled, unavailable, or candidates are empty, returns original candidates truncated to top_k.
        """
        k = top_k if top_k is not None else self.final_k

        if not candidates:
            return []

        model = self._get_model()
        if model is None:
            # Graceful fallback: return hybrid candidates sorted by original hybrid score
            return candidates[:k]

        try:
            # Form query-chunk text pairs
            pairs = [[query, c.get("text", "")] for c in candidates]
            scores = model.predict(pairs, batch_size=self.batch_size)

            reranked = []
            for candidate, score in zip(candidates, scores):
                item = candidate.copy()
                item["reranker_score"] = round(float(score), 4)
                # Store reranker score as primary score for final RAG display
                item["score"] = round(float(score), 4)
                reranked.append(item)

            # Sort by reranker score descending
            reranked.sort(key=lambda x: x["reranker_score"], reverse=True)
            logger.info(f"Reranked {len(candidates)} candidates -> top {min(k, len(reranked))} selected.")
            return reranked[:k]

        except Exception as e:
            logger.warning(f"CrossEncoder inference failed: {e}. Returning hybrid candidate baseline.")
            return candidates[:k]

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "model_name": self.model_name,
            "loaded": self._model is not None,
            "available": self._is_available
        }

reranker_service = RerankerService()
