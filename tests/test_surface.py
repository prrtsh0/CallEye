"""Surface tests: routing split, unlock API, and landing hygiene (no mic / no
service worker / no audio logging)."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import _UNLOCK_ATTEMPTS, app, settings

client = TestClient(app)

BASE = Path(__file__).resolve().parent.parent
SITE = BASE / "site"


# ---------- routing ----------
def test_landing_served_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "Slow the scam down." in r.text
    assert "Open the app" in r.text


def test_docs_served_at_root():
    r = client.get("/docs")
    assert r.status_code == 200
    assert "CallEye docs" in r.text


def test_app_served_at_app_slash():
    r = client.get("/app/")
    assert r.status_code == 200
    assert "Welcome to CallEye" in r.text
    assert "app.js" in r.text


def test_shared_tokens_served():
    r = client.get("/shared/tokens.css")
    assert r.status_code == 200
    assert "--navy-900" in r.text


def test_demo_fixture_served():
    r = client.get("/data/fixtures/demo_digital_arrest.json")
    assert r.status_code == 200
    assert "segments" in r.json()


def test_mictest_still_served():
    assert client.get("/mic-test").status_code == 200


# ---------- /api/practice (real detector) ----------
def test_practice_runs_real_detector():
    r = client.post("/api/practice/demo_digital_arrest")
    assert r.status_code == 200
    data = r.json()
    assert data["label"] == "scam"
    events = data["events"]
    assert events
    types = [e["type"] for e in events]
    assert "transcript" in types and "analysis" in types
    # The fixture is a clear scam: final analysis should be red.
    last = [e for e in events if e["type"] == "analysis"][-1]
    assert last["level"] == "red"


def test_practice_unknown_fixture_404():
    assert client.post("/api/practice/nope").status_code == 404


# ---------- /api/unlock ----------
def _set_live(enabled: bool):
    settings.gnani_mode = "live" if enabled else "mock"
    settings.invite_codes = "TEST123" if enabled else ""


def test_unlock_accepts_valid_code():
    _set_live(True)
    try:
        r = client.post("/api/unlock", json={"code": "test123"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "daily_allowance" in data
    finally:
        _set_live(False)


def test_unlock_rejects_invalid_code():
    _set_live(True)
    try:
        r = client.post("/api/unlock", json={"code": "WRONG"})
        assert r.status_code == 403
    finally:
        _set_live(False)


def test_unlock_rejected_when_live_disabled():
    _set_live(False)
    r = client.post("/api/unlock", json={"code": "TEST123"})
    assert r.status_code == 400


def test_unlock_rate_limited():
    _set_live(True)
    _UNLOCK_ATTEMPTS.clear()
    try:
        for _ in range(10):
            client.post("/api/unlock", json={"code": "WRONG"})
        last = client.post("/api/unlock", json={"code": "WRONG"})
        assert last.status_code == 429
    finally:
        _set_live(False)
        _UNLOCK_ATTEMPTS.clear()


# ---------- landing hygiene ----------
def _site_files():
    return [p for p in SITE.rglob("*") if p.is_file() and p.suffix in (".html", ".js", ".css")]


def test_site_has_no_getusermedia_or_serviceworker():
    found = [p.name for p in _site_files()
             if "getUserMedia" in p.read_text(errors="ignore")
             or "navigator.serviceWorker" in p.read_text(errors="ignore")]
    assert found == [], f"site/ must not contain mic/service-worker code: {found}"


def test_site_no_ws_or_login_references():
    found = [p.name for p in _site_files()
             if "/ws/listen" in p.read_text(errors="ignore")
             or "api/unlock" in p.read_text(errors="ignore")]
    assert found == [], f"site/ must not reference app internals: {found}"


def test_no_transcript_logged():
    # Landing demo JS must not console.log full transcripts.
    js = (SITE / "app.js").read_text(errors="ignore")
    assert "console.log" not in js


# ---------- assets ----------
def test_eval_json_built():
    assert (SITE / "data" / "eval.json").exists()


def test_og_image_built():
    assert (SITE / "assets" / "og-image.png").exists()
