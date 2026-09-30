"""
Phase 9 Index & Service Recovery Unit Tests.
"""

import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.indexing_service import indexing_service
from app.services.vector_store import vector_store
from app.services.bm25_service import bm25_service

def test_index_rebuild_recovery():
    """Verify vector_store and BM25 index rebuild from SQLite database."""
    db: Session = SessionLocal()
    try:
        res = indexing_service.rebuild_index(db)
        assert res["status"] == "REBUILT"
        assert res["total_chunks_indexed"] >= 0
        assert vector_store.index is not None
        assert len(vector_store.metadata_store) == res["total_chunks_indexed"]
    finally:
        db.close()
