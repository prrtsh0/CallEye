"""Stage tracking: authority, fear, isolation, urgency, ask."""
from __future__ import annotations

from app.detector.lexicon import PlaybookLexicon

STAGES = ("authority", "fear", "isolation", "urgency", "ask")


def detect_stages(lexicon: PlaybookLexicon, text: str) -> set[str]:
    """Return the set of stages that are present in *text*."""
    hit = set()
    for stage in STAGES:
        if lexicon.hit_count(stage, text) > 0:
            hit.add(stage)
    return hit
