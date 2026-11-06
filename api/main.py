"""CallEye FastAPI application."""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict, deque

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.auth import create_user, issue_token, require_user, revoke_token, user_by_email
from api.config import (
    APP_DIR,
    FIXTURES_DIR,
    LANDING_DIR,
    SHARED_DIR,
    Settings,
    get_settings,
)
from api.db import backend_name, get_connection, init_db
from api.gnani.credits import CreditTracker
from api.gnani.factory import get_file_stt_adapter
from api.guard import GuardManager
from api.relay import RelayHandler
from model.detector.engine import SessionAnalyzer
from model.detector.explain import build_explanation, guardian_note

LANGUAGES = ["hi", "hi-latn", "en"]

# Module-level singletons (created at import so the app works with or without a
# lifespan context manager, e.g. under a bare TestClient).
settings: Settings = get_settings()
guard = GuardManager(settings)
credits = CreditTracker(
    credits_per_minute=settings.stt_credits_per_minute,
    floor=settings.credit_floor,
)

_START_TIME = time.time()

# Numbers-only runtime counters for /admin/monitor.
_MONITOR = {"analyze": 0, "transcribe": 0, "practice": 0, "levels": Counter()}

# Move the API docs (Swagger/ReDoc) off /docs so the public docs page can live
# there. Swagger remains available at /swagger for development.
app = FastAPI(title="CallEye", version="1.0.0", docs_url="/swagger", redoc_url="/redoc")

# Ensure the user DB exists (safe to call repeatedly).
init_db()


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": settings.app_name}


# ---------- /api/auth (signup / login / me / logout) ----------
@app.post("/api/auth/signup")
async def signup(body: dict):
    email = (body.get("email") or "").strip().lower()
    name = (body.get("name") or "").strip()
    password = body.get("password") or ""
    if not email or "@" not in email or not name or len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="valid email, name, and password (6+ chars) required",
        )
    user_id = create_user(email, name, password)
    if user_id is None:
        raise HTTPException(status_code=409, detail="an account with that email already exists")
    return {"ok": True, "token": issue_token(user_id), "user": {"email": email, "name": name}}


@app.post("/api/auth/login")
async def login(body: dict):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    from api.auth import verify_password  # noqa: PLC0415  (avoids circular import)
    user = user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return {"ok": True, "token": issue_token(user["id"]),
            "user": {"email": user["email"], "name": user["name"]}}


@app.get("/api/auth/me")
async def me(user: dict = Depends(require_user)):
    return {"user": {"email": user["email"], "name": user["name"]}}


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(default="")):
    if authorization.lower().startswith("bearer "):
        revoke_token(authorization[7:].strip())
    return {"ok": True}


_UNLOCK_ATTEMPTS: dict[str, deque] = defaultdict(deque)
_UNLOCK_MAX_PER_HOUR = 10
_UNLOCK_WINDOW = 3600


def _unlock_rate_limited(ip: str) -> bool:
    now = time.time()
    q = _UNLOCK_ATTEMPTS[ip]
    while q and now - q[0] > _UNLOCK_WINDOW:
        q.popleft()
    if len(q) >= _UNLOCK_MAX_PER_HOUR:
        return True
    q.append(now)
    return False


@app.post("/api/unlock")
async def unlock(body: dict, request: Request):
    """Validate a live access code. Rate limited per IP."""
    if not settings.live_enabled:
        raise HTTPException(status_code=400, detail="live mode disabled")
    ip = request.client.host if request.client else "?"
    if _unlock_rate_limited(ip):
        raise HTTPException(status_code=429, detail="too many attempts")
    code = (body.get("code") or "").strip().upper()
    if code not in settings.invite_code_set:
        raise HTTPException(status_code=403, detail="invalid code")
    return {"ok": True, "daily_allowance": settings.daily_cap_per_device}


@app.get("/api/config")
async def api_config():
    return {
        "app": settings.app_name,
        "languages": LANGUAGES,
        "live_mode": settings.live_enabled,
        "mode": settings.effective_mode,
        "session_max_seconds": settings.session_max_seconds,
        "daily_cap_per_device": settings.daily_cap_per_device,
        "invite_required": settings.live_enabled,
        "app_url": settings.app_url,
    }


def _verdict(text: str) -> dict:
    analyzer = SessionAnalyzer()
    result = analyzer.analyze_update(text, True, 0.0)
    return {
        "text": text,
        "level": result.level,
        "screen_text": result.screen_text,
        "pressure": result.pressure,
        "lever": result.lever,
        "stages": result.stages,
        "reasons": result.reasons,
        "would_never_ask": result.would_never_ask,
        # The model's output (None when no model is present / falls back to rules).
        "p_scam": result.p_scam,
        "explanation": build_explanation(result),
        "guardian_note": guardian_note(result),
        "setup_detected": result.setup_detected,
    }


@app.post("/api/analyze")
async def analyze(body: dict, user: dict = Depends(require_user)):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    verdict = _verdict(text)
    _MONITOR["analyze"] += 1
    _MONITOR["levels"][verdict["level"]] += 1
    return verdict


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), lang: str = "hi",
                    user: dict = Depends(require_user)):
    audio = await file.read()
    adapter = get_file_stt_adapter(settings)
    result = await adapter.transcribe_file(audio, lang)
    verdict = _verdict(result.full_text)
    verdict["transcript"] = result.full_text
    _MONITOR["transcribe"] += 1
    _MONITOR["levels"][verdict["level"]] += 1
    return verdict


@app.post("/api/practice/{fixture}")
async def practice(fixture: str, user: dict = Depends(require_user)):
    """Replay a stored fixture through the REAL detector (SessionAnalyzer) and
    return the same event stream the live WebSocket relay emits. This lets the
    app's practice mode exercise the actual Python model, not a browser-side
    simulation. Zero credits (no STT/network)."""
    path = FIXTURES_DIR / f"{fixture}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="fixture not found")
    data = json.loads(path.read_text(encoding="utf-8"))

    analyzer = SessionAnalyzer()
    events = []
    for seg in data.get("segments", []):
        text = str(seg.get("text", "")).strip()
        t = float(seg.get("t", 0.0))
        if not text:
            continue
        result = analyzer.analyze_update(text, True, t)
        events.append({
            "type": "transcript", "text": text, "final": True, "t": round(t, 1),
        })
        events.append({
            "type": "analysis",
            "level": result.level,
            "screen_text": result.screen_text,
            "pressure": result.pressure,
            "lever": result.lever,
            "stages": list(result.stages),
            "reasons": list(result.reasons),
            "would_never_ask": result.would_never_ask,
            "explanation": build_explanation(result),
            "guardian_note": guardian_note(result),
            "setup_detected": result.setup_detected,
            "t": round(t, 1),
        })
    _MONITOR["practice"] += 1
    return {"id": data.get("id", fixture), "label": data.get("label", ""),
            "events": events}


@app.websocket("/ws/listen")
async def ws_listen(websocket: WebSocket):
    await RelayHandler(websocket, settings, guard).run()


def require_admin(x_admin_token: str = Header(default="")) -> None:
    """Fail-closed guard for /admin/* routes: always requires a matching
    ADMIN_TOKEN; when none is configured the admin endpoints stay disabled."""
    expected = settings.admin_token
    if not expected:
        raise HTTPException(
            status_code=401,
            detail="ADMIN_TOKEN is not configured; admin endpoints are disabled",
        )
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="invalid admin token")


@app.get("/admin/usage", dependencies=[Depends(require_admin)])
async def admin_usage():
    return {"guard": guard.usage(), "credits": credits.snapshot()}


@app.get("/admin/monitor", dependencies=[Depends(require_admin)])
async def admin_monitor():
    """Numbers-only health/monitor stats (no PII, no transcripts)."""
    users = sessions = 0
    try:
        with get_connection() as conn:
            users = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
            sessions = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
    except Exception:
        pass  # DB not ready yet / read-only
    return {
        "users": users,
        "sessions": sessions,
        "calls": dict(_MONITOR),
        "backend": backend_name(),
        "uptime_s": int(time.time() - _START_TIME),
    }


@app.get("/mic-test")
async def mic_test():
    return FileResponse(APP_DIR / "mic-test.html")


@app.get("/docs")
async def docs_page():
    return FileResponse(LANDING_DIR / "docs.html")


# Shared static assets (tokens, doodles, result-view module). Mounted before
# the landing so `/shared/...` resolves regardless of the landing mount.
app.mount("/shared", StaticFiles(directory=SHARED_DIR), name="shared")

# Demo fixture data used by the landing demo (static, read-only).
app.mount("/data/fixtures", StaticFiles(directory=FIXTURES_DIR), name="fixtures")

# The installable PWA (scope /app/). Mounted before the landing root.
app.mount("/app", StaticFiles(directory=APP_DIR, html=True), name="app")

# Public landing at / (must be mounted after API routes).
app.mount("/", StaticFiles(directory=LANDING_DIR, html=True), name="site")
