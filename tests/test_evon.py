"""Tests for the Evon reasoning integration and plain-language explanations."""
from __future__ import annotations

import asyncio

from api.config import get_settings
from api.gnani.factory import get_reason_adapter
from api.gnani.types import ReasonRequest
from model.detector.engine import SessionAnalyzer


def test_red_explanation_mentions_guardian():
    az = SessionAnalyzer()
    res = az.analyze_update("mujhe aapka OTP chahiye", True, 0.0)
    assert res.level == "red"
    assert "scam" in res.explanation.lower()
    assert "guardian" in res.guardian_note.lower()


def test_amber_explanation_present():
    az = SessionAnalyzer()
    res = az.analyze_update("aapne lottery jeeta hai", True, 0.0)
    res = az.analyze_update("prize ke liye ek fee pay karni hogi", True, 3.0)
    assert res.level == "amber"
    assert res.explanation


def test_mock_reason_adapter_returns_explanation():
    adapter = get_reason_adapter(get_settings())
    req = ReasonRequest(language="hi", transcript="x", level="amber", reasons=["pressure"])
    resp = asyncio.run(adapter.explain(req))
    assert resp.explanation
    assert resp.guardian_note == ""


def test_setup_buildup_is_detected_before_ask():
    az = SessionAnalyzer()
    for t, text in [
        (0.0, "main police thana se bol raha hoon"),
        (3.0, "aapke naam par case darj hua hai"),
        (6.0, "aapko arrest ho sakta hai"),
        (9.0, "kisi ko nahi batana"),
    ]:
        res = az.analyze_update(text, True, t)
    assert res.setup_detected is True
    assert res.level in ("amber", "red")
