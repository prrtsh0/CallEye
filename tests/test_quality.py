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
    assert not (BASE_DIR / ".env").exists(), ".env must not be committed"


def test_env_example_exists():
    assert (BASE_DIR / ".env.example").exists()


def test_readme_exists():
    assert (BASE_DIR / "README.md").exists()
