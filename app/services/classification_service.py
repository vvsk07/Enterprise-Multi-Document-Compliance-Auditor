"""
Document Classification Service using TF-IDF + Logistic Regression.
Trains, evaluates, persists, and predicts document categories with confidence scoring.
"""

import os
import csv
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support

from app.config import settings
from app.core.logging import logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = BASE_DIR / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "document_classifier.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"
DATASET_PATH = BASE_DIR / "data" / "training" / "document_classification.csv"

# Pre-defined categories
DOCUMENT_CATEGORIES = [
    "Contract",
    "NDA",
    "Employment Agreement",
    "Company Policy",
    "Compliance Document",
    "Invoice",
    "Financial Document",
    "Legal Document",
    "Other"
]

class DocumentClassificationService:
    def __init__(self, confidence_threshold: float = 0.15):
        self.confidence_threshold = confidence_threshold
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[LogisticRegression] = None
        
        # Load pre-trained model if available
        self.load_model()

    def train(self, csv_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Trains TF-IDF + Logistic Regression classifier on CSV dataset.
        Saves trained model and vectorizer to disk.
        Returns evaluation metrics dictionary.
        """
        data_file = Path(csv_path) if csv_path else DATASET_PATH
        if not data_file.exists():
            raise FileNotFoundError(f"Training dataset not found at '{data_file}'.")

        logger.info(f"Loading training data from '{data_file}'...")
        X_list, y_list = [], []
        with open(data_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "text" in row and "label" in row:
                    X_list.append(row["text"].strip())
                    y_list.append(row["label"].strip())

        if not X_list or not y_list:
            raise ValueError("Training CSV must contain valid 'text' and 'label' rows.")

        X = np.array(X_list)
        y = np.array(y_list)

        # Stratified train-test split (or standard split if small sample size)
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

        logger.info(f"Training classifier on {len(X_train)} samples, testing on {len(X_test)} samples...")

        # Initialize TF-IDF Vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True
        )
        X_train_vec = self.vectorizer.fit_transform(X_train)
        X_test_vec = self.vectorizer.transform(X_test)

        # Train Logistic Regression
        self.classifier = LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver="lbfgs",
            random_state=42
        )
        self.classifier.fit(X_train_vec, y_train)

        # Evaluate model
        y_pred = self.classifier.predict(X_test_vec)
        acc = float(accuracy_score(y_test, y_pred))
        
        precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
            y_test, y_pred, average="macro", zero_division=0
        )
        precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(
            y_test, y_pred, average="weighted", zero_division=0
        )

        metrics = {
            "accuracy": round(acc, 4),
            "macro_precision": round(float(precision_macro), 4),
            "macro_recall": round(float(recall_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            "weighted_f1": round(float(f1_weighted), 4),
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }

        # Save model artifacts
        self.save_model()
        logger.info(f"Classifier successfully trained & saved. Metrics: {metrics}")
        return metrics

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predicts document category and confidence score for a text string.
        Returns: (predicted_category, confidence_score)
        """
        if not text or not text.strip():
            return "Other", 0.0

        if not self.classifier or not self.vectorizer:
            logger.info("Classifier not loaded in memory. Attempting auto-training...")
            try:
                self.train()
            except Exception as e:
                logger.error(f"Auto-training failed: {e}. Returning default classification.")
                return "Other", 0.0

        try:
            vec = self.vectorizer.transform([text])
            probabilities = self.classifier.predict_proba(vec)[0]
            max_idx = np.argmax(probabilities)
            confidence = float(probabilities[max_idx])
            predicted_label = str(self.classifier.classes_[max_idx])

            if confidence < self.confidence_threshold:
                logger.info(f"Low classification confidence ({confidence:.2f} < {self.confidence_threshold}). Assigning 'Other'.")
                return "Other", round(confidence, 4)

            return predicted_label, round(confidence, 4)
        except Exception as e:
            logger.error(f"Classification prediction error: {e}")
            return "Other", 0.0

    def save_model(self):
        """Saves vectorizer and classifier model to disk."""
        if self.classifier and self.vectorizer:
            joblib.dump(self.classifier, MODEL_PATH)
            joblib.dump(self.vectorizer, VECTORIZER_PATH)
            logger.info(f"Saved classifier models to '{MODEL_DIR}'.")

    def load_model(self) -> bool:
        """Loads trained vectorizer and classifier models from disk if present."""
        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            try:
                self.classifier = joblib.load(MODEL_PATH)
                self.vectorizer = joblib.load(VECTORIZER_PATH)
                logger.info(f"Loaded classifier model from '{MODEL_PATH}'.")
                return True
            except Exception as e:
                logger.warning(f"Failed to load classifier model: {e}")
                return False
        return False

classification_service = DocumentClassificationService()
