"""
Master Document Processing Orchestrator Service.
Coordinates file type routing, text extraction, normalization, chunking, and database persistence.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, Entity
from app.services.pdf_processor import pdf_processor
from app.services.docx_processor import docx_processor
from app.services.txt_processor import txt_processor
from app.services.text_normalization import text_normalizer
from app.services.chunking_service import chunking_service
from app.services.classification_service import classification_service
from app.services.ner_service import ner_service
from app.services.entity_service import entity_normalizer
from app.core.logging import logger

class DocumentProcessorService:
    def process_document(self, db: Session, document_id: str) -> Document:
        """
        Orchestrates full ingestion pipeline for a given document:
        1. Fetch Document from DB
        2. Set status to PROCESSING
        3. Extract text page-by-page (PDF), section-by-section (DOCX), or raw (TXT)
        4. Normalize text
        5. Generate sentence-aware chunks
        6. Persist DocumentChunks and update Document status
        """
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        logger.info(f"Starting ingestion pipeline for document '{doc.filename}' (ID: {document_id}).")
        doc.document_status = "PROCESSING"
        doc.processing_error = None
        db.commit()

        try:
            file_path = str(Path(doc.file_path).resolve())
            file_type = doc.file_type.lower()
            
            raw_text_parts = []
            all_chunks = []
            page_count = 0
            doc_ocr_required = False

            if file_type == "pdf":
                pages_data, doc_ocr_required, total_pages = pdf_processor.process_pdf(file_path)
                page_count = total_pages
                
                for p_info in pages_data:
                    p_num = p_info["page_number"]
                    p_text = p_info["text"]
                    if p_text:
                        raw_text_parts.append(f"--- Page {p_num} ---\n{p_text}")
                        norm_p_text = text_normalizer.normalize_text(p_text)
                        p_chunks = chunking_service.chunk_text(
                            text=norm_p_text,
                            document_id=doc.document_id,
                            filename=doc.filename,
                            page_number=p_num,
                            section=None
                        )
                        all_chunks.extend(p_chunks)

            elif file_type == "docx":
                sections_data, combined_text = docx_processor.process_docx(file_path)
                page_count = 1
                
                for s_info in sections_data:
                    sec_name = s_info["section"]
                    sec_text = s_info["text"]
                    if sec_text:
                        raw_text_parts.append(f"--- Section: {sec_name} ---\n{sec_text}")
                        norm_sec_text = text_normalizer.normalize_text(sec_text)
                        sec_chunks = chunking_service.chunk_text(
                            text=norm_sec_text,
                            document_id=doc.document_id,
                            filename=doc.filename,
                            page_number=None,
                            section=sec_name
                        )
                        all_chunks.extend(sec_chunks)

            elif file_type == "txt":
                raw_txt = txt_processor.process_txt(file_path)
                page_count = 1
                raw_text_parts.append(raw_txt)
                
                norm_txt = text_normalizer.normalize_text(raw_txt)
                txt_chunks = chunking_service.chunk_text(
                    text=norm_txt,
                    document_id=doc.document_id,
                    filename=doc.filename,
                    page_number=1,
                    section="General"
                )
                all_chunks.extend(txt_chunks)
            else:
                raise ValueError(f"Unsupported file format: {file_type}")

            # Assemble full extracted & normalized text
            raw_full_text = "\n\n".join(raw_text_parts)
            norm_full_text = text_normalizer.normalize_text(raw_full_text)

            # Delete existing chunks and entities if re-processing
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.document_id).delete()
            db.query(Entity).filter(Entity.document_id == doc.document_id).delete()

            # Insert new chunks into DB
            db_chunks = []
            for idx, c_data in enumerate(all_chunks):
                db_chunk = DocumentChunk(
                    chunk_id=c_data["chunk_id"],
                    document_id=doc.document_id,
                    chunk_index=idx,
                    page_number=c_data.get("page_number"),
                    section=c_data.get("section"),
                    text=c_data["text"],
                    metadata_json=json.dumps(c_data.get("metadata", {}))
                )
                db_chunks.append(db_chunk)

            db.add_all(db_chunks)

            # Perform Document Classification
            try:
                category, conf = classification_service.predict(norm_full_text)
                doc.predicted_document_type = category
                doc.classification_confidence = conf
            except Exception as cls_err:
                logger.error(f"Automatic classification failed for {document_id}: {cls_err}")
                doc.predicted_document_type = "Other"
                doc.classification_confidence = 0.0

            # Perform NER Entity Extraction
            try:
                extracted_ents = ner_service.extract_entities(norm_full_text)
                db_entities = []
                for e_data in extracted_ents:
                    norm_text = entity_normalizer.normalize_entity_text(e_data["text"], e_data["label"])
                    ent_obj = Entity(
                        entity_id=str(uuid.uuid4()),
                        document_id=doc.document_id,
                        chunk_id=None,
                        entity_text=e_data["text"],
                        normalized_text=norm_text,
                        entity_label=e_data["label"],
                        start_position=e_data["start"],
                        end_position=e_data["end"],
                        context=e_data["context"]
                    )
                    db_entities.append(ent_obj)
                db.add_all(db_entities)
            except Exception as ner_err:
                logger.error(f"Automatic NER failed for {document_id}: {ner_err}")

            # Update Document attributes
            doc.extracted_text = raw_full_text
            doc.normalized_text = norm_full_text
            doc.page_count = page_count
            doc.ocr_required = doc_ocr_required
            
            if doc_ocr_required and not any(c.text.strip() for c in db_chunks):
                doc.document_status = "OCR_REQUIRED"
            elif doc_ocr_required:
                doc.document_status = "PARTIALLY_PROCESSED"
            else:
                doc.document_status = "PROCESSED"

            db.commit()
            db.refresh(doc)

            logger.info(f"Successfully processed document '{doc.filename}' with status '{doc.document_status}'. Chunks: {len(db_chunks)}, Category: {doc.predicted_document_type}.")
            return doc

        except Exception as e:
            logger.error(f"Error during document processing pipeline for {document_id}: {e}")
            db.rollback()
            doc.document_status = "FAILED"
            doc.processing_error = str(e)
            db.commit()
            db.refresh(doc)
            return doc

document_processor_service = DocumentProcessorService()
