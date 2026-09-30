"""
Phase 3 Evaluation Script for Document Classification & Named Entity Recognition.
Reports Accuracy, Precision, Recall, F1-scores, and Confusion Matrix.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.classification_service import classification_service
from app.services.ner_service import ner_service
from app.services.metadata_extractor import metadata_extractor

def run_evaluation():
    print("=" * 60)
    print("      ENTERPRISE COMPLIANCE AUDITOR - PHASE 3 NLP EVALUATION")
    print("=" * 60)

    # 1. Evaluate Document Classifier
    print("\n[-] Evaluating TF-IDF + Logistic Regression Classifier...")
    try:
        metrics = classification_service.train()
        print(f"  [+] Accuracy         : {metrics['accuracy']:.4f}")
        print(f"  [+] Macro Precision  : {metrics['macro_precision']:.4f}")
        print(f"  [+] Macro Recall     : {metrics['macro_recall']:.4f}")
        print(f"  [+] Macro F1-Score   : {metrics['macro_f1']:.4f}")
        print(f"  [+] Weighted F1-Score: {metrics['weighted_f1']:.4f}")
        print(f"  [+] Train Samples    : {metrics['train_samples']}")
        print(f"  [+] Test Samples     : {metrics['test_samples']}")
    except Exception as e:
        print(f"  [FAIL] Classification evaluation failed: {e}")
        return False

    # 2. Evaluate NER & Custom Domain Entity Extraction
    print("\n[-] Evaluating spaCy NER & Custom Entity Extractor...")
    sample_text = (
        "This Master Services Agreement AGR-2026-991 is between Acme Global Inc and Vertex Technologies LLC. "
        "Effective date is January 15, 2026. Payment of $50,000 USD is due within 30 days. "
        "Governing law is Delaware state court under Section 4.1."
    )

    entities = ner_service.extract_entities(sample_text)
    print(f"  [+] Sample Input Text Length: {len(sample_text)} characters")
    print(f"  [+] Extracted Entities Count: {len(entities)}")
    
    for ent in entities:
        print(f"      - {ent['label']:<15}: '{ent['text']}'")

    # 3. Evaluate Metadata Extractor
    print("\n[-] Evaluating Deterministic Metadata Extractor...")
    metadata = metadata_extractor.extract_metadata(sample_text)
    for cat, items in metadata.items():
        if items:
            item_texts = [i["text"] for i in items]
            print(f"      - {cat:<20}: {item_texts}")

    print("\n" + "=" * 60)
    print(" PHASE 3 NLP EVALUATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
