"""Realtime STT adapter for Gnani Prisma.

IMPORTANT: The exact endpoint, headers, and frame format must be confirmed from
the Gnani docs (docs/gnani-notes.md). This implementation follows the contract
described in the Engineering Handbook and is intentionally isolated here so that
only this file needs updating if the real wire format differs.
"""
from __future__ import annotations

import asyncio
import json

import websockets

from app.gnani.base import STTAdapter
from app.gnani.types import STTResult


class RealtimeSTTAdapter(STTAdapter):
    def __init__(self, ws_url: str, api_key: str):
        self.ws_url = ws_url
        self.api_key = api_key

    async def transcribe_file(self, audio: bytes, language: str, **kw) -> STTResult:
        # File (REST) STT is handled by FileSTTAdapter; here we raise to signal
        # that the caller should use the file adapter for whole files.
        raise NotImplementedError("Use FileSTTAdapter for whole-file transcription")

    async def stream(self, language, on_segment, sample_rate=16000, on_state=None):
        headers = {"X-API-Key-ID": self.api_key}
        async with websockets.connect(self.ws_url, additional_headers=headers) as ws:
            # Send a start/config frame (format to be confirmed from docs).
            await ws.send(json.dumps({
                "type": "start", "lang": language, "sample_rate": sample_rate}))
            if on_state:
                on_state("connected")

            async def _reader():
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("type") == "transcript":
                        text = msg.get("text", "")
                        final = bool(msg.get("final", True))
                        t = float(msg.get("t", 0))
                        await on_segment(text, final, t)

            reader_task = asyncio.create_task(_reader())
            try:
                # Control loop: the relay feeds audio by sending bytes into this
                # generator. We forward them to the socket.
                while True:
                    frame = yield
                    if frame is None:
                        break
                    await ws.send(frame)
            finally:
                reader_task.cancel()
                try:
                    await ws.send(json.dumps({"type": "stop"}))
                except Exception:
                    pass
