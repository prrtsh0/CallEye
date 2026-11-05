"""CallEye FastAPI application."""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR, Settings, get_settings
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

app = FastAPI(title="CallEye", version="1.0.0")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/config")
async def api_config():
    return {
        "app": settings.app_name,
        "languages": LANGUAGES,
        "live_mode": settings.effective_mode == "live",
        "mode": settings.effective_mode,
        "session_max_seconds": settings.session_max_seconds,
        "daily_cap_per_device": settings.daily_cap_per_device,
        "invite_required": bool(settings.invite_code_set),
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


# Serve the PWA static frontend (must be mounted after API routes).
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
