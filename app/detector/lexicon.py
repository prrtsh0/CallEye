"""Loads playbook YAML into a single lexicon of matchable phrase lists."""
from __future__ import annotations

import yaml

from app.config import PLAYBOOKS_DIR
from app.detector.normalize import normalize

_CATEGORIES = ("authority", "fear", "isolation", "urgency", "ask",
               "would_never", "money_demand", "warning_cues", "emergency",
               "reward")


class PlaybookLexicon:
    def __init__(self, playbooks: list[str] | None = None):
        self.playbooks = playbooks or ["family.yaml", "student.yaml"]
        self.phrases: dict[str, list[tuple[str, float]]] = {c: [] for c in _CATEGORIES}
        self._load()

    def _load(self) -> None:
        for name in self.playbooks:
            path = PLAYBOOKS_DIR / name
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for cat in _CATEGORIES:
                entries = data.get(cat) or []
                for e in entries:
                    pat = normalize(str(e.get("text", "")))
                    if not pat:
                        continue
                    w = float(e.get("weight", 1.0))
                    self.phrases[cat].append((pat, w))

    def matches(self, category: str, text: str) -> list[tuple[str, float]]:
        """Return phrase/weight pairs whose phrase occurs in normalized text."""
        norm = normalize(text)
        if not norm:
            return []
        hits = []
        for pat, w in self.phrases.get(category, []):
            if pat in norm:
                hits.append((pat, w))
        return hits

    def weighted_score(self, category: str, text: str) -> float:
        return sum(w for _, w in self.matches(category, text))

    def hit_count(self, category: str, text: str) -> int:
        return len(self.matches(category, text))
