"""Would-never ask detection with warning-vs-request handling.

A bank, police, or government body never asks for OTP/PIN/CVV/UPI
PIN/passwords, remote-access apps, safe-account transfers, or money to avoid
arrest. Such a term is a red "would-never ask" — UNLESS a negation/warning cue
(mat, nahi, never, do not, kabhi nahi) sits within about six tokens of the term
*in the same sentence*, in which case it's a genuine warning and not an ask.

We evaluate per sentence so a cue in one sentence does not mask an ask in the
next.
"""
from __future__ import annotations

import re

from app.detector.lexicon import PlaybookLexicon
from app.detector.normalize import normalize

_WINDOW = 6
_SENT_SPLIT = re.compile(r"[.!?।]")


def would_never_ask(lexicon: PlaybookLexicon, text: str) -> tuple[bool, str]:
    norm = normalize(text)
    if not norm:
        return False, ""
    cue_patterns = [p for p, _ in lexicon.phrases["warning_cues"]]

    def has_cue_near(sentence: str, idx: int, pat: str) -> bool:
        prefix = sentence[:idx].strip()
        suffix = sentence[idx + len(pat):].strip()
        before = prefix.split()[-_WINDOW:] if prefix else []
        after = suffix.split()[:_WINDOW] if suffix else []
        window = before + after
        return any(any(cue in w for cue in cue_patterns) for w in window)

    for sentence in _SENT_SPLIT.split(norm):
        if not sentence.strip():
            continue
        for pat, _ in lexicon.phrases["would_never"]:
            start = 0
            while True:
                idx = sentence.find(pat, start)
                if idx < 0:
                    break
                if not has_cue_near(sentence, idx, pat):
                    return True, pat
                start = idx + len(pat)
    return False, ""
