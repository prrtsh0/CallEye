"""Lever identification (what the scam is leaning on)."""
from __future__ import annotations

from app.detector.lexicon import PlaybookLexicon


def detect_lever(lexicon: PlaybookLexicon, text: str) -> str:
    """Return a lever string by priority:
    emergency > authority > account loss > reward > payment > unknown.
    """
    if lexicon.hit_count("emergency", text) > 0:
        return "emergency"
    if lexicon.hit_count("authority", text) > 0 and \
            lexicon.hit_count("fear", text) > 0:
        return "authority"
    if lexicon.hit_count("reward", text) > 0:
        return "reward"
    ask_hits = lexicon.matches("ask", text)
    ask_text = " ".join(p for p, _ in ask_hits)
    if any(k in ask_text for k in ("otp", "pin", "cvv", "upi", "password",
                                    "verify", "card number", "account number")):
        return "account loss"
    if lexicon.hit_count("money_demand", text) > 0:
        return "payment"
    if lexicon.hit_count("contactity", text) > 0:
        return "authority"
    return "unknown"
