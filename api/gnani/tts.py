"""Timbre TTS adapter (REST)."""
from __future__ import annotations

import httpx

from api.gnani.base import TTSAdapter
from api.gnani.types import TTSAudio, TTSRequest


class TimbreTTSAdapter(TTSAdapter):
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key

    async def synthesize(self, request: TTSRequest) -> TTSAudio:
        headers = {"X-API-Key-ID": self.api_key}
        payload = {"language": request.language, "text": request.text}
        if request.voice:
            payload["voice"] = request.voice
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.url}/tts", json=payload, headers=headers)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "audio/mpeg")
            return TTSAudio(data=resp.content, content_type=ctype)
