"""Train the small TF-IDF + logistic regression scam classifier and evaluate it
against the held-out test split.

Usage: python -m eval.train
Reads labeled calls from data/calls/train.json (train split), writes the model to
model/detector/model.joblib, then scores the held-out test split and writes a
metrics report to eval/model_report.md. If the model is absent at runtime the
detector falls back to rules only.
"""
from __future__ import annotations

import json

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score

from api.config import BASE_DIR, DATA_DIR, MODEL_PATH

EVAL_DIR = BASE_DIR / "model" / "eval"
REPORT_PATH = EVAL_DIR / "model_report.md"


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


def train(rows: list[tuple[str, int]]) -> tuple[TfidfVectorizer, LogisticRegression]:
    texts = [r[0] for r in rows]
    labels = [r[1] for r in rows]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(2, 5), max_features=20000, sublinear_tf=True)
    X = vectorizer.fit_transform(texts)
    model = LogisticRegression(max_iter=2000)
    model.fit(X, labels)
    return vectorizer, model


def write_report(y_true: list[int], y_pred: list[int], n_train: int) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Model evaluation (classifier only)",
        "",
        "This is the standalone TF-IDF + logistic-regression classifier, evaluated",
        "on the held-out test split. It is one signal blended into the hybrid",
        "detector, never used alone.",
        "",
        f"- Training calls: **{n_train}**",
        f"- Test calls: **{len(y_true)}**",
        f"- Accuracy: **{accuracy_score(y_true, y_pred):.3f}**",
        f"- Precision (scam): **{precision_score(y_true, y_pred):.3f}**",
        f"- Recall (scam): **{recall_score(y_true, y_pred):.3f}**",
        "",
        "> Honest caveat: with a small labeled set, these numbers are illustrative,",
        "> not production-grade. The hybrid detector always also applies the rules.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = load_labeled("train")
    if len(rows) < 4:
        print("Not enough training data; skipping model training.")
        return

    vectorizer, model = train(rows)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, MODEL_PATH)

    # Evaluate on the held-out test split (never used in training).
    test_rows = load_labeled("test")
    if test_rows:
        y_true = [r[1] for r in test_rows]
        X_test = vectorizer.transform([r[0] for r in test_rows])
        y_pred = list(model.predict(X_test))
        write_report(y_true, y_pred, len(rows))
        print(f"Trained on {len(rows)} calls -> {MODEL_PATH}")
        print(f"Evaluated on {len(test_rows)} held-out test calls -> {REPORT_PATH}")
    else:
        print(f"Trained on {len(rows)} calls -> {MODEL_PATH} (no test split to evaluate)")


if __name__ == "__main__":
    main()
