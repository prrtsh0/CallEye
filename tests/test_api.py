from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_config():
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "languages" in data
    assert data["mode"] == "mock"


def test_analyze_scam(auth_client):
    r = auth_client("POST", "/api/analyze", json={
        "text": "main police thana se bol raha hoon. aapke naam par case darj hua hai. "
                "aapko arrest ho sakta hai. kisi ko mat batana. bail ke liye paise transfer "
                "karo. mujhe aapka OTP chahiye."
    })
    assert r.status_code == 200
    assert r.json()["level"] == "red"


def test_analyze_genuine(auth_client):
    r = auth_client("POST", "/api/analyze", json={
        "text": "aapke bank account me transaction hui hai. kisi ko OTP mat batana. "
                "bank kabhi bhi OTP nahi maangta."
    })
    assert r.status_code == 200
    assert r.json()["level"] in ("green", "amber")


def test_analyze_empty_returns_400(auth_client):
    r = auth_client("POST", "/api/analyze", json={"text": ""})
    assert r.status_code == 400


def test_analyze_requires_auth(client):
    r = client.post("/api/analyze", json={"text": "hello"})
    assert r.status_code == 401


def test_admin_usage_requires_token():
    r = client.get("/admin/usage")
    assert r.status_code == 200  # no token configured => open


def test_admin_monitor_returns_numbers_only():
    r = client.get("/admin/monitor")
    assert r.status_code == 200
    data = r.json()
    assert {"users", "sessions", "calls", "backend", "uptime_s"} <= set(data)
    assert isinstance(data["users"], int)
    assert isinstance(data["sessions"], int)
    assert isinstance(data["uptime_s"], int)
    # numbers-only: no emails, transcripts, or passwords
    assert "email" not in str(data).lower()
    assert "transcript" not in str(data).lower()
