"""Mock adapters used when no network/key is available. Development and CI use
these and consume zero credits. Mock STT replays recorded transcript fixtures.
"""
from __future__ import annotations

import asyncio
import json
import struct

from api.config import FIXTURES_DIR, Settings
from api.gnani.base import STTAdapter, TTSAdapter
from api.gnani.types import STTResult, TranscriptSegment, TTSAudio, TTSRequest

DEFAULT_FIXTURE = "scam_demo_digital_arrest"


class MockSTTAdapter(STTAdapter):
    """Replays a stored transcript as a stream of live segments."""

    def __init__(self, settings: Settings, fixture: str | None = None):
        self.settings = settings
        self.fixture = fixture or DEFAULT_FIXTURE
        self._segments = self._load(self.fixture)

    def select_fixture(self, name: str) -> None:
        """Switch the mock replay to a different recorded transcript."""
        self.fixture = name or DEFAULT_FIXTURE
        self._segments = self._load(self.fixture)

    @staticmethod
    def _load(name: str) -> list[TranscriptSegment]:
        path = FIXTURES_DIR / f"{name}.json"
        if not path.exists():
            # Fall back to a simple built-in line so mock mode always works.
            return [TranscriptSegment(text="ye ek mock test call hai", final=True, t=0.0)]
        with path.open(encoding="utf-8") as fh:
            doc = json.load(fh)
        return [TranscriptSegment(text=s.get("text", ""), final=True, t=float(s.get("t", 0)))
                for s in doc.get("segments", [])]

    async def transcribe_file(self, audio: bytes, language: str, **kw) -> STTResult:
        await asyncio.sleep(0.01)
        return STTResult(segments=list(self._segments))

    async def stream(self, language, on_segment, sample_rate=16000, on_state=None):
        prev_t = 0.0
        for seg in self._segments:
            gap = max(0.0, seg.t - prev_t)
            if gap:
                await asyncio.sleep(min(gap, 1.5))
            prev_t = seg.t
            await on_segment(seg.text, True, seg.t)
            yield
        # Signal end of stream.
        yield None


class MockTTSAdapter(TTSAdapter):
    """Returns a placeholder/silent clip so playback wiring can be tested."""

    async def synthesize(self, request: TTSRequest) -> TTSAudio:
        await asyncio.sleep(0.005)
        # A tiny WAV header for a 0.1s silent clip (8 kHz mono 8-bit).
        hdr = bytearray()
        hdr += b"RIFF"
        hdr += struct.pack("<I", 36 + 800)
        hdr += b"WAVEfmt "
        hdr += struct.pack("<IHHIIHH", 16, 1, 1, 8000, 8000, 1, 8)
        hdr += b"data"
        hdr += struct.pack("<I", 800)
        hdr += bytes(800)  # silence
        return TTSAudio(data=bytes(hdr), content_type="audio/wav")
