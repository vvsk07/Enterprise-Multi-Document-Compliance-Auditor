"""
Comprehensive Pytest Test Suite for Phase 4:
Embeddings, FAISS Vector Store, Indexing, Semantic Search, and Grounded RAG Pipeline.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store
from app.services.indexing_service import indexing_service
from app.services.search_service import search_service
from app.services.rag_service import rag_service
from app.models.document import Document, DocumentChunk

# Configure in-memory test database with StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"


def test_embedding_service():
    dim = embedding_service.get_embedding_dimension()
    assert dim == 384

    vec = embedding_service.embed_text("Confidentiality obligations agreement")
    assert len(vec) == 384
    assert isinstance(vec[0], float)

    batch_vecs = embedding_service.embed_texts(["Text 1", "Text 2"])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 384

    empty_vec = embedding_service.embed_text("")
    assert len(empty_vec) == 384
    assert empty_vec[0] == 0.0


def test_vector_store():
    vector_store.clear_index()
    chunk_ids = ["chunk-1", "chunk-2"]
    texts = [
        "This agreement shall expire on December 31, 2026.",
        "Either party may terminate with 30 days written notice."
    ]
    vectors = embedding_service.embed_texts(texts)
    metadata = [
        {"chunk_id": "chunk-1", "filename": "test.txt", "page_number": 1, "text": texts[0]},
        {"chunk_id": "chunk-2", "filename": "test.txt", "page_number": 2, "text": texts[1]}
    ]

    vector_store.add_embeddings(chunk_ids, vectors, metadata)
    assert vector_store.index.ntotal >= 2

    query_vec = embedding_service.embed_text("termination notice")
    results = vector_store.similarity_search(query_vec, top_k=2)
    assert len(results) >= 1
    assert "terminate" in results[0]["text"].lower() or "expire" in results[0]["text"].lower()


def test_indexing_service_and_search_api():
    # 1. Ingest sample file
    txt_path = SAMPLE_DIR / "compliant_contract.txt"
    with open(txt_path, "rb") as f:
        content = f.read()
    up_res = client.post(
        "/documents/upload",
        files=[("files", ("compliant_contract.txt", content, "text/plain"))]
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["uploaded_files"][0]["document_id"]

    # 2. Test GET /index/status
    st_res = client.get("/index/status")
    assert st_res.status_code == 200
    status_data = st_res.json()
    assert status_data["embedding_dimension"] == 384
    assert status_data["indexed_chunks"] > 0

    # 3. Test POST /search
    search_res = client.post(
        "/search",
        json={"query": "What is the governing law?", "top_k": 3}
    )
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert s_data["total_results"] > 0
    assert "score" in s_data["results"][0]


def test_rag_pipeline():
    # Test RAG Query with evidence citations
    rag_res = client.post(
        "/rag/query",
        json={"query": "What are the termination notice conditions?", "top_k": 3, "minimum_score": 0.10}
    )
    assert rag_res.status_code == 200
    r_data = rag_res.json()
    assert "question" in r_data
    assert "answer" in r_data
    assert len(r_data["citations"]) > 0
    assert len(r_data["sources"]) > 0
    assert r_data["retrieval_count"] > 0


def test_rag_insufficient_evidence():
    # Query with high minimum_score threshold to test insufficient evidence handling
    rag_res = client.post(
        "/rag/query",
        json={"query": "quantum supercomputing teleportation algorithm", "top_k": 3, "minimum_score": 0.95}
    )
    assert rag_res.status_code == 200
    r_data = rag_res.json()
    assert "Insufficient evidence" in r_data["answer"]
    assert len(r_data["citations"]) == 0
