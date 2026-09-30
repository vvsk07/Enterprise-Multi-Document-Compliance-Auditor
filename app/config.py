"""
Application Configuration Module.
Loads environment variables and settings YAML file.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Enterprise-Grade Multi-Document Intelligence & Compliance Auditor"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/compliance_auditor.db"
    
    DATA_DIR: Path = BASE_DIR / "data"
    REPORTS_DIR: Path = BASE_DIR / "data" / "reports"
    UPLOADS_DIR: Path = BASE_DIR / "data" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    SAMPLE_DOCS_DIR: Path = BASE_DIR / "data" / "sample_documents"
    CONFIG_DIR: Path = BASE_DIR / "configs"
    
    VECTOR_DB_TYPE: str = "faiss"
    VECTOR_INDEX_PATH: Path = BASE_DIR / "data" / "processed" / "faiss_index.bin"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LLM_BASE_URL: str = ""
    
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
for directory in [settings.UPLOADS_DIR, settings.PROCESSED_DIR, settings.SAMPLE_DOCS_DIR, settings.CONFIG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

def load_yaml_config(filename: str = "settings.yaml") -> Dict[str, Any]:
    config_path = settings.CONFIG_DIR / filename
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

yaml_config = load_yaml_config()

def get_document_processing_config() -> Dict[str, Any]:
    return yaml_config.get("document_processing", {
        "max_file_size_mb": 25,
        "supported_extensions": [".pdf", ".docx", ".txt"],
        "chunk_size": 500,
        "chunk_overlap": 50
    })

def get_retrieval_config() -> Dict[str, Any]:
    return yaml_config.get("retrieval", {
        "bm25_weight": 0.40,
        "dense_weight": 0.60,
        "candidate_k": 20,
        "final_k": 5,
        "persistence_path": "data/processed/bm25_index.json"
    })

def get_reranker_config() -> Dict[str, Any]:
    return yaml_config.get("reranker", {
        "enabled": True,
        "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "candidate_k": 20,
        "final_k": 5,
        "batch_size": 8
    })

def get_security_config() -> Dict[str, Any]:
    return yaml_config.get("security", {
        "enabled": False,
        "api_key_header": "X-API-Key",
        "api_key_env_var": "AUDITOR_API_KEY"
    })

def get_api_config() -> Dict[str, Any]:
    return yaml_config.get("api", {
        "max_query_length": 2000,
        "max_top_k": 50,
        "max_upload_size_mb": 25,
        "rate_limit": {
            "enabled": True,
            "requests_per_minute": 60
        }
    })

def get_logging_config() -> Dict[str, Any]:
    return yaml_config.get("logging", {
        "level": "INFO",
        "format": "json"
    })


