"""Train the small TF-IDF + logistic regression scam classifier.

Usage: python -m eval.train
Reads labeled calls from data/calls/*.json (train split) and writes the model to
app/detector/model.joblib. If the model is absent at runtime the detector falls
back to rules only.
"""
from __future__ import annotations

import json

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.config import DATA_DIR, MODEL_PATH


def load_labeled(split: str) -> list[tuple[str, int]]:
    path = DATA_DIR / "calls" / f"{split}.json"
    if not path.exists():
        return []
    docs = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for doc in docs:
        text = " ".join(s["text"] for s in doc.get("segments", []))
        label = 1 if doc.get("label") == "scam" else 0
        rows.append((text, label))
    return rows


def main() -> None:
    rows = load_labeled("train")
    if len(rows) < 4:
        print("Not enough training data; skipping model training.")
        return
    texts = [r[0] for r in rows]
    labels = [r[1] for r in rows]

    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(2, 5), max_features=20000, sublinear_tf=True)
    X = vectorizer.fit_transform(texts)
    model = LogisticRegression(max_iter=2000)
    model.fit(X, labels)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, MODEL_PATH)
    print(f"Trained on {len(rows)} calls -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
