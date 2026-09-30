"""
FAISS Vector Store Service.
Manages 384-dimensional inner product (cosine) FAISS index and associated JSON chunk metadata with persistence.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss

from app.config import settings
from app.core.logging import logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_DIR = BASE_DIR / "data" / "vector_store"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX_PATH = VECTOR_DIR / "faiss_index.bin"
METADATA_MAP_PATH = VECTOR_DIR / "metadata_map.json"

class FAISSVectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index: Optional[faiss.IndexFlatIP] = None
        self.metadata_store: List[Dict[str, Any]] = []  # List of chunk metadata matching FAISS id sequence
        
        self.load_index()

    def _init_new_index(self):
        """Initializes a new FAISS IndexFlatIP (cosine similarity for normalized vectors)."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata_store = []
        logger.info(f"Initialized new empty FAISS IndexFlatIP with dimension {self.dimension}.")

    def add_embeddings(
        self,
        chunk_ids: List[str],
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]]
    ):
        """
        Adds normalized vectors and corresponding chunk metadata into FAISS index and persists to disk.
        """
        if not vectors or not chunk_ids:
            return

        if self.index is None:
            self._init_new_index()

        np_vectors = np.array(vectors, dtype=np.float32)
        # Ensure vectors are normalized for cosine similarity
        faiss.normalize_L2(np_vectors)

        self.index.add(np_vectors)
        self.metadata_store.extend(metadata_list)

        self.save_index()
        logger.info(f"Added {len(chunk_ids)} vectors to FAISS vector store. Total index count: {self.index.ntotal}.")

    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search against FAISS index with optional metadata filtering.
        Returns ranked list of result dicts:
        [{"chunk_id": "...", "score": 0.85, "filename": "...", "text": "...", "page_number": 1}]
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Similarity search called on empty FAISS index.")
            return []

        query_np = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query_np)

        # Retrieve extra candidates if metadata filtering is requested
        search_k = min(top_k * 5 if filters else top_k, self.index.ntotal)
        scores, indices = self.index.search(query_np, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata_store):
                continue
            
            meta = self.metadata_store[idx].copy()
            meta["score"] = round(float(score), 4)

            # Apply metadata filters if provided
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
        """Persists FAISS index binary and metadata map JSON to disk."""
        if self.index is not None:
            faiss.write_index(self.index, str(FAISS_INDEX_PATH))
            with open(METADATA_MAP_PATH, "w", encoding="utf-8") as f:
                json.dump(self.metadata_store, f, indent=2)
            logger.info(f"Saved FAISS index ({self.index.ntotal} vectors) and metadata map to '{VECTOR_DIR}'.")

    def load_index(self) -> bool:
        """Loads FAISS index binary and metadata map JSON from disk if present."""
        if FAISS_INDEX_PATH.exists() and METADATA_MAP_PATH.exists():
            try:
                self.index = faiss.read_index(str(FAISS_INDEX_PATH))
                with open(METADATA_MAP_PATH, "r", encoding="utf-8") as f:
                    self.metadata_store = json.load(f)
                logger.info(f"Loaded FAISS index from disk. Total vectors: {self.index.ntotal}.")
                return True
            except Exception as e:
                logger.error(f"Failed to load FAISS index from disk: {e}")
                self._init_new_index()
                return False
        else:
            self._init_new_index()
            return False

    def clear_index(self):
        """Clears FAISS index and metadata store."""
        self._init_new_index()
        if FAISS_INDEX_PATH.exists():
            os.remove(FAISS_INDEX_PATH)
        if METADATA_MAP_PATH.exists():
            os.remove(METADATA_MAP_PATH)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_indexed_chunks": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "index_type": "FAISS_IndexFlatIP",
            "index_path": str(FAISS_INDEX_PATH),
            "metadata_path": str(METADATA_MAP_PATH)
        }

vector_store = FAISSVectorStore()
