"""
BM25 Lexical Retrieval Service.
Implements lexical search using rank-bm25 over document chunks with persistence and metadata filtering.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from app.config import settings, get_retrieval_config
from app.core.logging import logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_DIR = BASE_DIR / "data" / "vector_store"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

BM25_INDEX_PATH = VECTOR_DIR / "bm25_index.json"

def tokenize_text(text: str) -> List[str]:
    """Simple alphanumeric lowercased tokenization for BM25 indexing and querying."""
    if not text:
        return []
    return re.findall(r"\w+", text.lower())

class BM25Service:
    def __init__(self):
        self.metadata_store: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.load_index()

    def _build_bm25(self):
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
        else:
            self.bm25 = None

    def add_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        metadata_list: List[Dict[str, Any]]
    ):
        """Adds document chunks to BM25 index and persists to disk."""
        if not chunk_ids or not texts:
            return

        for chunk_id, text, meta in zip(chunk_ids, texts, metadata_list):
            tokens = tokenize_text(text)
            chunk_meta = meta.copy()
            chunk_meta["chunk_id"] = chunk_id
            chunk_meta["text"] = text

            self.metadata_store.append(chunk_meta)
            self.corpus_tokens.append(tokens)

        self._build_bm25()
        self.save_index()
        logger.info(f"Added {len(chunk_ids)} chunks to BM25 index. Total count: {len(self.metadata_store)}.")

    def search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs lexical BM25 search over indexed chunks with optional metadata filtering.
        Returns candidate dicts with BM25 score.
        """
        if self.bm25 is None or not self.metadata_store:
            logger.warning("BM25 search called on empty index.")
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        
        # Rank by score descending
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0.0 and len(results) >= top_k:
                # Cutoff zero-score results if we already have top_k, but keep if needed
                break

            meta = self.metadata_store[idx].copy()
            meta["score"] = round(score, 4)
            meta["bm25_score"] = round(score, 4)

            # Metadata filtering
            if filters:
                match = True
                for k, v in filters.items():
                    if v is not None and meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            results.append(meta)
            if len(results) >= top_k:
                break

        return results

    def save_index(self):
        """Persists BM25 metadata and tokens to disk."""
        data = {
            "metadata_store": self.metadata_store,
            "corpus_tokens": self.corpus_tokens
        }
        with open(BM25_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved BM25 index ({len(self.metadata_store)} chunks) to '{BM25_INDEX_PATH}'.")

    def load_index(self) -> bool:
        """Loads BM25 index from disk if available."""
        if BM25_INDEX_PATH.exists():
            try:
                with open(BM25_INDEX_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.metadata_store = data.get("metadata_store", [])
                self.corpus_tokens = data.get("corpus_tokens", [])
                self._build_bm25()
                logger.info(f"Loaded BM25 index from disk. Total chunks: {len(self.metadata_store)}.")
                return True
            except Exception as e:
                logger.error(f"Failed to load BM25 index: {e}")
                self.metadata_store = []
                self.corpus_tokens = []
                self.bm25 = None
                return False
        else:
            self.metadata_store = []
            self.corpus_tokens = []
            self.bm25 = None
            return False

    def clear_index(self):
        """Clears BM25 index and persistence file."""
        self.metadata_store = []
        self.corpus_tokens = []
        self.bm25 = None
        if BM25_INDEX_PATH.exists():
            BM25_INDEX_PATH.unlink()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_indexed_chunks": len(self.metadata_store),
            "index_path": str(BM25_INDEX_PATH),
            "status": "ready" if self.bm25 is not None else "empty"
        }

bm25_service = BM25Service()
