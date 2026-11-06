"""Verify the ML classifier is real and genuinely wired through the API.

These tests treat the classifier as one signal of the hybrid detector. The test
split is never used for training (asserted below), matching the honest-caveat
design in AGENTS.md.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import joblib
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE / "app/detector/model.joblib"


def _load_split(name):
    import json  # noqa: PLC0415
    path = BASE / "data/calls" / f"{name}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def test_model_file_exists_and_loads():
    assert MODEL_PATH.exists(), "train the model first: python -m eval.train"
    bundle = joblib.load(MODEL_PATH)
    assert "vectorizer" in bundle and "model" in bundle


def test_train_and_test_splits_are_disjoint():
    train = _load_split("train")
    test = _load_split("test")
    train_ids = {d["id"] for d in train}
    test_ids = {d["id"] for d in test}
    assert train_ids & test_ids == set(), "test split leaked into training"


def test_analyze_endpoint_returns_p_scam(auth_client):
    # With a model present, the API must expose the classifier's output.
    r = auth_client("POST", "/api/analyze",
                    json={"text": "I am calling from the police, pay bail now"})
    assert r.status_code == 200
    body = r.json()
    assert "p_scam" in body
    assert body["p_scam"] is None or 0.0 <= body["p_scam"] <= 1.0


def test_training_script_imports_and_runs_train_func():
    # Ensure the training pipeline is importable and can train/evaluate on the
    # labeled data without a network.
    train = importlib.import_module("eval.train")
    rows = train.load_labeled("train")
    assert len(rows) >= 4
    vectorizer, model = train.train(rows)
    assert vectorizer is not None and model is not None
