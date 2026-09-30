"""
Database Session, Engine Setup, and Safe Migration.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from app.models.document import Document, DocumentChunk, Entity, ComplianceFinding, ContradictionFinding, RiskAssessment
    Base.metadata.create_all(bind=engine)

    
    # Safe column migrations for SQLite
    if "sqlite" in settings.DATABASE_URL:
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN predicted_document_type VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE contradiction_findings ADD COLUMN similarity_score FLOAT"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE contradiction_findings ADD COLUMN contradiction_score FLOAT"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE contradiction_findings ADD COLUMN evidence_a TEXT"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE contradiction_findings ADD COLUMN evidence_b TEXT"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE contradiction_findings ADD COLUMN source_a VARCHAR"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE contradiction_findings ADD COLUMN source_b VARCHAR"))
            except Exception:
                pass
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
