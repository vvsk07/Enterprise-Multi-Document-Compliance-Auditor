"""
Retrieval-Augmented Generation (RAG) Service with Evidence Grounding & Citations.
Executes semantic retrieval and produces extractive/grounded answers with traceable document sources.
"""

from typing import List, Dict, Any, Optional
from app.services.search_service import search_service
from app.core.logging import logger

class RAGService:
    def __init__(self, min_relevance_threshold: float = 0.25):
        self.min_relevance_threshold = min_relevance_threshold

    def _generate_extractive_answer(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Generates an evidence-grounded answer from retrieved chunks.
        Extracts relevant sentences containing key query terms and synthesizes a concise response.
        """
        if not retrieved_chunks:
            return "Insufficient evidence in the indexed documents."

        q_terms = set(question.lower().replace("?", "").replace(".", "").split())
        stop_words = {"what", "is", "the", "are", "of", "and", "to", "in", "for", "a", "an", "this", "that", "how"}
        meaningful_terms = q_terms - stop_words

        answer_sentences = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            text = chunk.get("text", "")
            sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
            
            for s in sentences:
                s_lower = s.lower()
                # Check sentence term overlap
                if any(term in s_lower for term in meaningful_terms):
                    if s not in answer_sentences:
                        answer_sentences.append(s)
                        if len(answer_sentences) >= 3:
                            break
            if len(answer_sentences) >= 3:
                break

        if not answer_sentences:
            # Fallback to top retrieved chunk text snippet
            top_text = retrieved_chunks[0].get("text", "").strip()
            first_sentence = top_text.split(".")[0] + "." if "." in top_text else top_text[:200]
            answer_sentences.append(first_sentence)

        combined_answer = " ".join(answer_sentences)
        return combined_answer

    def query_rag(
        self,
        question: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
        minimum_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes grounded RAG pipeline for a user question.
        Returns answer, citations, source list, and relevance metrics.
        """
        threshold = minimum_score if minimum_score is not None else self.min_relevance_threshold

        # 1. Retrieve top-k semantic matches
        retrieved_chunks = search_service.search(
            query=question,
            top_k=top_k,
            document_id=document_id,
            document_type=document_type,
            minimum_score=threshold
        )

        if not retrieved_chunks:
            logger.info(f"No chunks met relevance threshold ({threshold}) for question '{question}'.")
            return {
                "question": question,
                "answer": "Insufficient evidence in the indexed documents to answer this question.",
                "sources": [],
                "citations": [],
                "retrieval_count": 0,
                "max_score": 0.0
            }

        # 2. Synthesize Grounded Answer
        answer_text = self._generate_extractive_answer(question, retrieved_chunks)

        # 3. Construct Traceable Citations
        citations = []
        sources = []

        for idx, chunk in enumerate(retrieved_chunks, 1):
            fname = chunk.get("filename", "document")
            page = chunk.get("page_number")
            page_str = f"Page {page}" if page else "N/A"
            sec = chunk.get("section")
            sec_str = f"Section: {sec}" if sec else "General"
            
            citation_str = f"[{idx}] {fname} - {page_str} - {sec_str}"
            citations.append(citation_str)

            sources.append({
                "citation_index": idx,
                "chunk_id": chunk.get("chunk_id"),
                "document_id": chunk.get("document_id"),
                "filename": fname,
                "page_number": page,
                "section": sec,
                "relevance_score": chunk.get("score", 0.0),
                "text": chunk.get("text")
            })

        max_score = max(r.get("score", 0.0) for r in retrieved_chunks)
        logger.info(f"RAG query generated answer grounded in {len(sources)} sources (Max Score: {max_score:.4f}).")

        return {
            "question": question,
            "answer": answer_text,
            "citations": citations,
            "sources": sources,
            "retrieval_count": len(sources),
            "max_score": round(max_score, 4)
        }

rag_service = RAGService()
