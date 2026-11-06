"""Whole-file (REST) STT via Gnani Prisma file API."""
from __future__ import annotations

import httpx

from api.gnani.base import STTAdapter
from api.gnani.types import STTResult, TranscriptSegment


class FileSTTAdapter(STTAdapter):
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key

    async def transcribe_file(self, audio: bytes, language: str, **kw) -> STTResult:
        headers = {"X-API-Key-ID": self.api_key}
        url = f"{self.api_base}/stt/file"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, files={"audio": audio})
            resp.raise_for_status()
            data = resp.json()
        segments = []
        for s in data.get("segments", []):
            segments.append(TranscriptSegment(
                text=s.get("text", ""), final=True, t=float(s.get("t", 0.0))))
        return STTResult(segments=segments)

    async def stream(self, language, on_segment, sample_rate=16000, on_state=None):
        raise NotImplementedError("File adapter does not stream")
