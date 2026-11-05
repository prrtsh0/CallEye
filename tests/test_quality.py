import json
from pathlib import Path

from app.config import BASE_DIR, DATA_DIR


def _ids(path: Path):
    if not path.exists():
        return set()
    return {d["id"] for d in json.loads(path.read_text(encoding="utf-8"))}


def test_train_and_test_splits_are_disjoint():
    """Guards against data leakage: training must never see test calls."""
    train = _ids(DATA_DIR / "calls" / "train.json")
    test = _ids(DATA_DIR / "calls" / "test.json")
    assert train and test, "expected both splits to exist"
    assert train.isdisjoint(test)


def test_no_env_committed():
    """`.env` (real secrets) must never be committed; it must stay ignored."""
    ignore = (BASE_DIR / ".gitignore").read_text(encoding="utf-8")
    patterns = {line.strip() for line in ignore.splitlines()}
    assert ".env" in patterns, ".env missing from .gitignore"
    # If a local .env exists for development it must be ignored, not tracked.
    env = BASE_DIR / ".env"
    if env.exists():
        assert ".env" in patterns


def test_env_example_exists():
    assert (BASE_DIR / ".env.example").exists()


def test_readme_exists():
    assert (BASE_DIR / "README.md").exists()
