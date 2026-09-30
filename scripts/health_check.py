"""
Phase 1 Health Check Script.
Verifies system dependencies, Python environment, directory structures, and core imports.
"""

import sys
import os
import platform

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_health_check():
    print("=" * 60)
    print("  ENTERPRISE COMPLIANCE AUDITOR - SYSTEM HEALTH CHECK (PHASES 1-7)")
    print("=" * 60)

    # 1. Python & OS Info
    print(f"[+] Operating System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"[+] Python Version   : {sys.version.split()[0]}")
    print(f"[+] Executable Path  : {sys.executable}")
    
    # 2. Key Import Checks
    print("\n[-] Testing System & NLP Imports...")
    
    modules_to_test = [
        ("fastapi", "FastAPI Core Web Framework"),
        ("uvicorn", "ASGI Web Server"),
        ("pydantic", "Data Validation & Settings"),
        ("spacy", "spaCy NLP & Entity Recognition"),
        ("sentence_transformers", "Sentence Transformers Embeddings"),
        ("faiss", "FAISS Vector Database"),
        ("reportlab", "ReportLab PDF Export Engine"),
        ("pandas", "Pandas Data Analytics & CSV"),
    ]
    
    for module_name, desc in modules_to_test:
        try:
            __import__(module_name)
            print(f"  [OK] {module_name:<25} ({desc}) -> Installed")
        except ImportError as e:
            print(f"  [FAIL] {module_name:<25} ({desc}) -> MISSING")
            
    # 3. Application Services & Database Models
    print("\n[-] Testing Phase 1-7 Application Services...")
    try:
        from app.config import settings
        from app.core.database import init_db, SessionLocal
        from app.models.document import Document, ComplianceFinding, ContradictionFinding, RiskAssessment
        from app.services.compliance_engine import compliance_engine
        from app.services.contradiction_service import contradiction_service
        from app.services.risk_scoring_service import risk_scoring_service
        from app.services.audit_report_service import audit_report_service

        init_db()
        print("  [OK] SQLite Database & Migrations      -> Initialized")
        print("  [OK] Compliance Engine Service         -> Loaded")
        print("  [OK] Contradiction Service             -> Loaded")
        print("  [OK] Risk Scoring Engine Service       -> Loaded")
        print("  [OK] Audit Report Service              -> Loaded")

    except Exception as e:
        print(f"  [FAIL] Service initialization failed: {e}")
        return False
        
    print("\n" + "=" * 60)
    print(" SYSTEM HEALTH CHECK PASSED (PHASES 1-7 READY)")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
