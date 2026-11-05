"""Text normalization used across the detector."""
from __future__ import annotations

import re

_WS = re.compile(r"\s+")
_LOWER = re.compile(r"[A-Z]")

# Small transliteration-ish equivalences so we match both scripts reasonably.
_REPLACEMENTS = {
    "पुलिस": "police",
    "अरेस्ट": "arrest",
    "केस": "case",
    "बैंक": "bank",
    "अकाउंट": "account",
    "ओटीपी": "otp",
    "पासवर्ड": "password",
    "तुरंत": "turant",
    "अभी": "abhi",
}


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, and apply simple script equivalences."""
    t = text.lower()
    for src, dst in _REPLACEMENTS.items():
        t = t.replace(src, dst)
    return _WS.sub(" ", t).strip()


def tokens(text: str) -> list[str]:
    """Rough tokenization (whitespace split) for window checks."""
    return normalize(text).split()
