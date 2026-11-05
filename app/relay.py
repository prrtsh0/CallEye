"""Realtime WebSocket relay at /ws/listen.

The browser never sees the Gnani key: audio frames arrive here, are forwarded to
the STT adapter, transcripts are analysed by the detector, and verdict/event
JSON is streamed back to the browser.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket

from app.config import Settings
from app.detector.engine import SessionAnalyzer
from app.gnani import get_stt_adapter
from app.guard import GuardManager


class RelayHandler:
    def __init__(self, ws: WebSocket, settings: Settings, guard: GuardManager):
        self.ws = ws
        self.settings = settings
        self.guard = guard
        self.analyzer = SessionAnalyzer()
        self.stt = get_stt_adapter(settings)

    async def _send(self, queue: asyncio.Queue, payload: dict) -> None:
        await queue.put(json.dumps(payload))

    async def _writer(self, queue: asyncio.Queue) -> None:
        while True:
            item = await queue.get()
            await self.ws.send_text(item)

    async def _pump_mock(self, agen) -> None:
        """Advance the self-timed mock STT generator until it finishes."""
        try:
            async for _ in agen:
                pass
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    async def run(self) -> None:
        await self.ws.accept()
        queue: asyncio.Queue = asyncio.Queue()
        writer = asyncio.create_task(self._writer(queue))

        # 1) Expect the start control message.
        try:
            first = await self.ws.receive_text()
            start = json.loads(first)
        except Exception:
            await self.ws.close(code=1008)
            writer.cancel()
            return

        if start.get("type") != "start":
            await self.ws.send_text(json.dumps({"type": "error", "code": "bad_start"}))
            await self.ws.close(code=1008)
            writer.cancel()
            return

        lang = start.get("lang", "hi")
        code = start.get("code")
        device_id = start.get("device_id", "")

        # 2) Abuse guards.
        if not self.guard.check_invite(code):
            await self.ws.send_text(json.dumps({"type": "error", "code": "invite_required"}))
            await self.ws.close(code=1008)
            writer.cancel()
            return
        if not self.guard.check_device_cap(device_id):
            await self.ws.send_text(json.dumps({"type": "error", "code": "device_cap_exceeded"}))
            await self.ws.close(code=1008)
            writer.cancel()
            return

        ws_id = id(self.ws)
        self.guard.open_session(ws_id)
        self.guard.record_device(device_id)

        async def on_segment(text: str, final: bool, t: float) -> None:
            result = self.analyzer.analyze_update(text, final, t)
            await self._send(queue, {
                "type": "transcript", "text": text,
                "final": final, "t": round(t, 1),
            })
            await self._send(queue, {
                "type": "analysis",
                "level": result.level,
                "screen_text": result.screen_text,
                "pressure": result.pressure,
                "lever": result.lever,
                "stages": result.stages,
                "reasons": result.reasons,
                "would_never_ask": result.would_never_ask,
                "t": round(t, 1),
            })

        # 3) Open the STT session (primed).
        agen = self.stt.stream(lang, on_segment)
        try:
            await agen.__anext__()
        except StopAsyncIteration:
            pass

        # In mock mode the replay is self-timed: advance it on its own so the
        # demo works even before/without microphone audio. Live mode is driven by
        # the frames the browser sends.
        pump_task = None
        if self.settings.effective_mode == "mock":
            pump_task = asyncio.create_task(self._pump_mock(agen))

        try:
            while True:
                # 4) Budget check.
                seconds_left = self.settings.session_max_seconds - \
                    self.guard.session_elapsed(ws_id)
                if seconds_left <= 0:
                    await self._send(queue, {"type": "error", "code": "budget_exhausted"})
                    break

                msg = await self.ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg["type"] == "websocket.receive_text":
                    try:
                        data = json.loads(msg["text"])
                    except Exception:
                        continue
                    if data.get("type") == "stop":
                        break
                    continue
                if msg["type"] == "websocket.receive_bytes":
                    # Forward audio frames only in live mode (mock ignores them).
                    if pump_task is None:
                        try:
                            await agen.asend(msg["bytes"])
                        except StopAsyncIteration:
                            pass
        finally:
            if pump_task is not None:
                pump_task.cancel()
            try:
                await agen.aclose()
            except Exception:
                pass
            self.guard.close_session(ws_id)
            writer.cancel()
            try:
                await self.ws.close()
            except Exception:
                pass
