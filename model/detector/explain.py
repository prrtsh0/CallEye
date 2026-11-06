"""Plain-language explanations for each verdict level.

These strings are deliberately calm, honest, and non-alarming. A green result
always means "no warning signs so far", never "safe". They are also the offline
fallback used by MockReasonAdapter; in live mode the Evon adapter can replace
them with model-generated text.
"""
from __future__ import annotations

GREEN_EXPLANATION = (
    "No warning signs detected so far. Stay calm and verify the caller "
    "through official channels."
)
AMBER_EXPLANATION = (
    "Some pressure signs are present. Stop, take a breath, and verify "
    "before sharing anything."
)
RED_EXPLANATION = (
    "This call shows high-pressure scam signs. Hang up and tell your guardian."
)

_BASE = {
    "green": GREEN_EXPLANATION,
    "amber": AMBER_EXPLANATION,
    "red": RED_EXPLANATION,
}


def build_explanation(result) -> str:
    """Build a short human-readable explanation for an analytical snapshot.

    `result` needs `.level` and `.reasons` (a list of detected signal phrases).
    """
    level = getattr(result, "level", "green")
    base = _BASE.get(level, GREEN_EXPLANATION)
    reasons = getattr(result, "reasons", []) or []
    if level != "green" and reasons:
        top = ", ".join(reasons[:3])
        return f"{base} Signs noticed: {top}."
    return base


def guardian_note(result) -> str:
    """A note shown to the user when a guardian alert is raised."""
    level = getattr(result, "level", "green")
    if level == "red":
        return (
            "Alert sent to your guardian. Do not share any PIN, OTP, "
            "card, or UPI details."
        )
    return ""
