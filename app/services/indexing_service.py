"""
Chunk Indexing Orchestrator Service.
Reads DocumentChunk records from SQLite, generates dense embeddings, and populates FAISS vector store.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.services.bm25_service import bm25_service
from app.core.logging import logger

class IndexingService:
    def index_document(self, db: Session, document_id: str) -> Dict[str, Any]:
        """
        Indexes all chunks belonging to a single document into FAISS and BM25.
        Returns indexing summary statistics.
        """
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
        if not chunks:
            logger.warning(f"No chunks found to index for document '{document_id}'.")
            return {
                "document_id": document_id,
                "filename": doc.filename,
                "chunks_indexed": 0,
                "status": "NO_CHUNKS"
            }

        logger.info(f"Indexing {len(chunks)} chunks for document '{doc.filename}' (ID: {document_id})...")

        chunk_ids = []
        chunk_texts = []
        metadata_list = []

        for chunk in chunks:
            chunk_ids.append(chunk.chunk_id)
            chunk_texts.append(chunk.text)
            metadata_list.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "document_type": doc.predicted_document_type or "Unclassified",
                "text": chunk.text
            })

        # Generate embeddings in batch
        vectors = embedding_service.embed_texts(chunk_texts)

        # Add to FAISS vector store and BM25 service
        vector_store.add_embeddings(chunk_ids, vectors, metadata_list)
        bm25_service.add_chunks(chunk_ids, chunk_texts, metadata_list)

        logger.info(f"Successfully indexed {len(chunks)} chunks for document '{doc.filename}'.")
        return {
            "document_id": document_id,
            "filename": doc.filename,
            "chunks_indexed": len(chunks),
            "status": "INDEXED"
        }

    def rebuild_index(self, db: Session) -> Dict[str, Any]:
        """
        Wipes the FAISS and BM25 index and rebuilds store from all existing DocumentChunk records in SQLite.
        """
        logger.info("Rebuilding vector store and BM25 index from scratch...")
        vector_store.clear_index()
        bm25_service.clear_index()

        all_docs = db.query(Document).all()
        total_indexed = 0
        doc_count = 0

        for doc in all_docs:
            res = self.index_document(db, doc.document_id)
            total_indexed += res["chunks_indexed"]
            if res["chunks_indexed"] > 0:
                doc_count += 1

        logger.info(f"Index rebuild complete. Processed {doc_count} documents, {total_indexed} chunks.")
        return {
            "total_documents": len(all_docs),
            "indexed_documents": doc_count,
            "total_chunks_indexed": total_indexed,
            "status": "REBUILT"
        }


    def get_index_status(self, db: Session) -> Dict[str, Any]:
        """
        Returns vector index health, total vector counts, and database document statistics.
        """
        total_docs = db.query(Document).count()
        total_chunks = db.query(DocumentChunk).count()
        store_stats = vector_store.get_stats()

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "indexed_chunks": store_stats["total_indexed_chunks"],
            "embedding_dimension": store_stats["dimension"],
            "index_type": store_stats["index_type"],
            "embedding_model": embedding_service.model_name
        }

indexing_service = IndexingService()
