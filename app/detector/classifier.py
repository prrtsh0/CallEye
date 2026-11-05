"""Optional learned layer (TF-IDF + logistic regression).

The runtime only uses the classifier when a saved model exists. If the model
file is missing, the detector relies on rules alone (p_scam is None and the
decision engine treats it as neutral). Training happens through eval/train.py.
"""
from __future__ import annotations

import joblib

from app.config import MODEL_PATH


class ScamClassifier:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        if MODEL_PATH.exists():
            try:
                bundle = joblib.load(MODEL_PATH)
                self.vectorizer = bundle.get("vectorizer")
                self.model = bundle.get("model")
            except Exception:
                self.model = None
                self.vectorizer = None

    @property
    def available(self) -> bool:
        return self.model is not None and self.vectorizer is not None

    def p_scam(self, text: str) -> float | None:
        if not self.available:
            return None
        X = self.vectorizer.transform([text])
        proba = self.model.predict_proba(X)[0]
        classes = list(self.model.classes_)
        if 1 in classes:
            return float(proba[classes.index(1)])
        return float(proba[0])
