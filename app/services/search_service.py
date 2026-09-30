"""
Semantic Search Service.
Embeds user search queries and retrieves ranked document chunks with metadata filtering.
"""

from typing import List, Dict, Any, Optional
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.core.logging import logger

class SearchService:
    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
        page_number: Optional[int] = None,
        minimum_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic search against vector store with metadata filtering.
        Returns ranked list of matching chunk metadata dictionary results.
        """
        if not query or not query.strip():
            return []

        # Construct filters dict
        filters = {}
        if document_id:
            filters["document_id"] = document_id
        if document_type:
            filters["document_type"] = document_type
        if page_number:
            filters["page_number"] = page_number

        logger.info(f"Executing semantic search for query '{query[:40]}...' (top_k={top_k}, filters={filters})...")

        query_vector = embedding_service.embed_text(query)
        results = vector_store.similarity_search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters if filters else None
        )

        # Filter by minimum score threshold
        filtered_results = [r for r in results if r.get("score", 0.0) >= minimum_score]
        
        # Sort explicitly by relevance score descending
        filtered_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        logger.info(f"Search query returned {len(filtered_results)} matching chunks.")
        return filtered_results

search_service = SearchService()
