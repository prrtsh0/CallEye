"""CallEye FastAPI application."""
from __future__ import annotations

import json
import time
from collections import defaultdict, deque

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_DIR, FIXTURES_DIR, SHARED_DIR, SITE_DIR, STATIC_DIR, Settings, get_settings
from app.detector.engine import SessionAnalyzer
from app.gnani.credits import CreditTracker
from app.gnani.factory import get_file_stt_adapter
from app.guard import GuardManager
from app.relay import RelayHandler

LANGUAGES = ["hi", "hi-latn", "en"]

# Module-level singletons (created at import so the app works with or without a
# lifespan context manager, e.g. under a bare TestClient).
settings: Settings = get_settings()
guard = GuardManager(settings)
credits = CreditTracker(
    credits_per_minute=settings.stt_credits_per_minute,
    floor=settings.credit_floor,
)

# Move the API docs (Swagger/ReDoc) off /docs so the public docs page can live
# there. Swagger remains available at /swagger for development.
app = FastAPI(title="CallEye", version="1.0.0", docs_url="/swagger", redoc_url="/redoc")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": settings.app_name}


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
    }


@app.post("/api/analyze")
async def analyze(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    return _verdict(text)


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), lang: str = "hi"):
    audio = await file.read()
    adapter = get_file_stt_adapter(settings)
    result = await adapter.transcribe_file(audio, lang)
    verdict = _verdict(result.full_text)
    verdict["transcript"] = result.full_text
    return verdict


@app.post("/api/practice/{fixture}")
async def practice(fixture: str):
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
            "t": round(t, 1),
        })
    return {"id": data.get("id", fixture), "label": data.get("label", ""),
            "events": events}


@app.websocket("/ws/listen")
async def ws_listen(websocket: WebSocket):
    await RelayHandler(websocket, settings, guard).run()


@app.get("/admin/usage")
async def admin_usage(request: Request):
    token = request.headers.get("x-admin-token") or ""
    if settings.admin_token and token != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid admin token")
    return {"guard": guard.usage(), "credits": credits.snapshot()}


@app.get("/mic-test")
async def mic_test():
    return FileResponse(STATIC_DIR / "mic-test.html")


@app.get("/docs")
async def docs_page():
    return FileResponse(SITE_DIR / "docs.html")


# Shared static assets (tokens, doodles, result-view module). Mounted before
# the landing so `/shared/...` resolves regardless of the landing mount.
app.mount("/shared", StaticFiles(directory=SHARED_DIR), name="shared")

# Demo fixture data used by the landing demo (static, read-only).
app.mount("/data/fixtures", StaticFiles(directory=FIXTURES_DIR), name="fixtures")

# The installable PWA (scope /app/). Mounted before the landing root.
app.mount("/app", StaticFiles(directory=APP_DIR, html=True), name="app")

# Public landing at / (must be mounted after API routes).
app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
