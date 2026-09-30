"""
Embedding Service using Sentence Transformers (all-MiniLM-L6-v2).
Provides CPU-optimized dense vector embeddings for text chunks and search queries.
"""

from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.core.logging import logger

class EmbeddingService:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or getattr(settings, "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        self.model: Optional[SentenceTransformer] = None
        self.dimension = 384

    def load_model(self) -> SentenceTransformer:
        """Loads and caches the SentenceTransformer model on CPU."""
        if self.model is None:
            logger.info(f"Loading SentenceTransformer embedding model '{self.model_name}' on CPU...")
            try:
                self.model = SentenceTransformer(self.model_name, device="cpu")
                self.dimension = self.model.get_embedding_dimension() or 384
                logger.info(f"Embedding model successfully loaded. Vector Dimension: {self.dimension}.")
            except Exception as e:
                logger.error(f"Failed to load embedding model '{self.model_name}': {e}")
                raise RuntimeError(f"Embedding model initialization error: {e}")
        return self.model

    def get_embedding_dimension(self) -> int:
        if self.model is None:
            self.load_model()
        return self.dimension

    def embed_text(self, text: str) -> List[float]:
        """Generates a 384-dimensional embedding vector for a single text string."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        model = self.load_model()
        embedding = model.encode(text.strip(), convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    def embed_single(self, text: str) -> List[float]:
        """Alias for embed_text."""
        return self.embed_text(text)


    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generates normalized vector embeddings for a list of text strings in batches."""
        if not texts:
            return []

        cleaned_texts = [t.strip() if t and t.strip() else " " for t in texts]
        model = self.load_model()
        embeddings = model.encode(
            cleaned_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.tolist()

embedding_service = EmbeddingService()
