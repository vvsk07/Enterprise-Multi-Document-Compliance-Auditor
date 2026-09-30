"""
Sentence/Paragraph-Aware Text Chunking Service.
Reads chunk size and overlap from configs/settings.yaml.
Calculates word-based token chunks preserving sentence boundaries.
"""

import re
import uuid
from typing import List, Dict, Any, Optional
from app.config import settings, get_document_processing_config
from app.core.logging import logger

class ChunkingService:
    def __init__(self):
        doc_cfg = get_document_processing_config()
        self.chunk_size_words = doc_cfg.get("chunk_size", 500)
        self.chunk_overlap_words = doc_cfg.get("chunk_overlap", 50)

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Splits text into sentences using regex boundary detection.
        """
        sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9])')
        sentences = sentence_end.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(
        self,
        text: str,
        document_id: str,
        filename: str,
        page_number: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunks text into sentence-aware blocks of approximately `chunk_size_words` words with `chunk_overlap_words` overlap.
        Returns list of chunk dicts ready for DocumentChunk DB storage.
        """
        if not text or not text.strip():
            return []

        sentences = self._split_into_sentences(text)
        chunks = []
        
        current_words = []
        current_sentence_buffer = []
        
        chunk_idx = 0
        char_cursor = 0

        for sentence in sentences:
            words = sentence.split()
            
            if len(current_words) + len(words) > self.chunk_size_words and current_words:
                chunk_str = " ".join(current_sentence_buffer)
                start_char = char_cursor
                end_char = char_cursor + len(chunk_str)
                
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": chunk_idx,
                    "page_number": page_number,
                    "section": section,
                    "text": chunk_str,
                    "metadata": {
                        "word_count": len(current_words),
                        "start_char": start_char,
                        "end_char": end_char,
                        "chunk_unit": "words"
                    }
                })
                
                chunk_idx += 1
                char_cursor += len(chunk_str)
                
                # Apply overlap by keeping last N words from sentence buffer
                overlap_words = 0
                new_sentence_buffer = []
                new_words = []
                
                for s in reversed(current_sentence_buffer):
                    s_words = s.split()
                    if overlap_words + len(s_words) <= self.chunk_overlap_words:
                        new_sentence_buffer.insert(0, s)
                        new_words = s_words + new_words
                        overlap_words += len(s_words)
                    else:
                        break
                        
                current_sentence_buffer = new_sentence_buffer
                current_words = new_words

            current_sentence_buffer.append(sentence)
            current_words.extend(words)

        # Flush final remaining chunk
        if current_sentence_buffer:
            chunk_str = " ".join(current_sentence_buffer)
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk_idx,
                "page_number": page_number,
                "section": section,
                "text": chunk_str,
                "metadata": {
                    "word_count": len(current_words),
                    "start_char": char_cursor,
                    "end_char": char_cursor + len(chunk_str),
                    "chunk_unit": "words"
                }
            })

        logger.info(f"Generated {len(chunks)} chunks for document {document_id} (Page: {page_number}, Section: {section}).")
        return chunks

chunking_service = ChunkingService()
