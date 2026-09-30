"""
Advanced RAG Pipeline Service.
Implements multi-stage retrieval-augmented generation:
Query Analysis -> Hybrid BM25+FAISS Search -> Reranking -> Deduplication & Diversity -> Evidence Grounding -> Citations & Retrieval Trace.
"""

from typing import List, Dict, Any, Optional
from app.services.query_analysis_service import query_analysis_service
from app.services.hybrid_search_service import hybrid_search_service
from app.services.reranker_service import reranker_service
from app.services.bm25_service import bm25_service
from app.services.vector_store import vector_store
from app.services.embedding_service import embedding_service
from app.core.logging import logger

class AdvancedRAGService:
    def __init__(self, min_evidence_threshold: float = 0.15):
        self.min_evidence_threshold = min_evidence_threshold

    def _deduplicate_and_diversify(
        self,
        candidates: List[Dict[str, Any]],
        max_chunks: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates retrieved chunks based on text similarity and promotes document diversity.
        """
        seen_texts = set()
        unique_chunks = []

        for c in candidates:
            text_snippet = c.get("text", "").strip()[:150].lower()
            if text_snippet in seen_texts:
                continue
            seen_texts.add(text_snippet)
            unique_chunks.append(c)
            if len(unique_chunks) >= max_chunks:
                break

        return unique_chunks

    def _generate_extractive_answer(
        self,
        question: str,
        query_analysis: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Generates grounded, extractive answer from selected evidence chunks.
        """
        if not chunks:
            return "Insufficient evidence in the indexed documents."

        q_terms = set(question.lower().replace("?", "").replace(".", "").split())
        stop_words = {"what", "is", "the", "are", "of", "and", "to", "in", "for", "a", "an", "this", "that", "how", "with"}
        meaningful_terms = q_terms - stop_words

        extracted_sentences = []
        for chunk in chunks:
            text = chunk.get("text", "")
            sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
            for sentence in sentences:
                s_lower = sentence.lower()
                if any(term in s_lower for term in meaningful_terms):
                    if sentence not in extracted_sentences:
                        extracted_sentences.append(sentence)
                        if len(extracted_sentences) >= 3:
                            break
            if len(extracted_sentences) >= 3:
                break

        if not extracted_sentences:
            top_text = chunks[0].get("text", "").strip()
            first_sentence = top_text.split(".")[0] + "." if "." in top_text else top_text[:200]
            extracted_sentences.append(first_sentence)

        answer = " ".join(extracted_sentences)
        return answer

    def query(
        self,
        question: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
        bm25_weight: float = 0.40,
        dense_weight: float = 0.60,
        minimum_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes Advanced Grounded RAG with full retrieval tracing and citations.
        """
        if not question or not question.strip():
            return {
                "question": question,
                "answer": "Insufficient evidence in the indexed documents.",
                "confidence": 0.0,
                "citations": [],
                "sources": [],
                "retrieval": {
                    "bm25_candidates": 0,
                    "dense_candidates": 0,
                    "fused_candidates": 0,
                    "reranked_candidates": 0
                }
            }

        threshold = minimum_score if minimum_score is not None else self.min_evidence_threshold

        # Step 1: Query Analysis
        q_analysis = query_analysis_service.analyze_query(question)

        # Filters
        filters = {}
        if document_id:
            filters["document_id"] = document_id
        elif document_type:
            filters["document_type"] = document_type
        elif q_analysis.get("document_scope") and q_analysis["document_scope"] != "All":
            filters["document_type"] = q_analysis["document_scope"]

        # Step 2: Hybrid Candidate Retrieval (BM25 + FAISS)
        candidate_k = max(20, top_k * 4)
        
        # Raw retrieval counts for tracing
        bm25_raw = bm25_service.search(question, top_k=candidate_k, filters=filters if filters else None)
        
        query_vec = embedding_service.embed_single(question)
        dense_raw = vector_store.similarity_search(query_vec, top_k=candidate_k, filters=filters if filters else None)

        fused_candidates = hybrid_search_service.search(
            query=question,
            top_k=candidate_k,
            filters=filters if filters else None,
            bm25_weight=bm25_weight,
            dense_weight=dense_weight
        )

        # Step 3: Cross-Encoder Reranking
        reranked_candidates = reranker_service.rerank(
            query=question,
            candidates=fused_candidates,
            top_k=candidate_k
        )

        # Step 4: Context Deduplication & Diversity Selection
        selected_evidence = self._deduplicate_and_diversify(reranked_candidates, max_chunks=top_k)

        # Filter by threshold
        valid_evidence = [c for c in selected_evidence if c.get("score", 0.0) >= threshold]

        if not valid_evidence:
            logger.info(f"No candidates satisfied minimum evidence threshold ({threshold}).")
            return {
                "question": question,
                "answer": "Insufficient evidence in the indexed documents.",
                "confidence": 0.0,
                "citations": [],
                "sources": [],
                "retrieval": {
                    "bm25_candidates": len(bm25_raw),
                    "dense_candidates": len(dense_raw),
                    "fused_candidates": len(fused_candidates),
                    "reranked_candidates": len(reranked_candidates)
                }
            }

        # Step 5: Answer Generation & Citations
        answer_text = self._generate_extractive_answer(question, q_analysis, valid_evidence)

        top_score = max(c.get("score", 0.0) for c in valid_evidence)
        confidence = round(min(1.0, max(0.0, (top_score + 1.0) / 2.0 if top_score < 0 else top_score)), 2)

        citations = []
        sources = []
        for idx, chunk in enumerate(valid_evidence, 1):
            fname = chunk.get("filename", "document")
            page = chunk.get("page_number")
            page_str = f"Page {page}" if page else "N/A"
            sec = chunk.get("section")
            sec_str = f"Section: {sec}" if sec else "General"

            citations.append(f"[{idx}] {fname} - {page_str} - {sec_str}")
            sources.append({
                "citation_index": idx,
                "chunk_id": chunk.get("chunk_id"),
                "document_id": chunk.get("document_id"),
                "filename": fname,
                "page_number": page,
                "section": sec,
                "score": chunk.get("score", 0.0),
                "bm25_score": chunk.get("raw_bm25", 0.0),
                "dense_score": chunk.get("raw_dense", 0.0),
                "reranker_score": chunk.get("reranker_score", 0.0),
                "text": chunk.get("text")
            })

        return {
            "question": question,
            "answer": answer_text,
            "confidence": confidence,
            "citations": citations,
            "sources": sources,
            "retrieval": {
                "bm25_candidates": len(bm25_raw),
                "dense_candidates": len(dense_raw),
                "fused_candidates": len(fused_candidates),
                "reranked_candidates": len(valid_evidence)
            }
        }

advanced_rag_service = AdvancedRAGService()
