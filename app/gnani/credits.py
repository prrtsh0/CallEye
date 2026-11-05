"""Credit estimation and usage logging (in-memory, numbers only).

No audio, transcript, or PII is ever kept here — just counters.
"""
from __future__ import annotations

import threading


class CreditTracker:
    def __init__(self, credits_per_minute: float, floor: float):
        self.credits_per_minute = credits_per_minute
        self.floor = floor
        self._lock = threading.Lock()
        self._stt_seconds = 0.0
        self._tts_calls = 0
        self._sessions = 0

    def record_stt_seconds(self, seconds: float) -> None:
        with self._lock:
            self._stt_seconds += max(0.0, seconds)

    def record_tts(self) -> None:
        with self._lock:
            self._tts_calls += 1

    def record_session(self) -> None:
        with self._lock:
            self._sessions += 1

    @property
    def estimated_credits(self) -> float:
        with self._lock:
            minutes = self._stt_seconds / 60.0
            return minutes * self.credits_per_minute

    def below_floor(self) -> bool:
        return self.estimated_credits >= self.floor

    def snapshot(self) -> dict:
        with self._lock:
            est = (self._stt_seconds / 60.0) * self.credits_per_minute
            return {
                "stt_seconds": round(self._stt_seconds, 1),
                "tts_calls": self._tts_calls,
                "sessions": self._sessions,
                "estimated_credits": round(est, 3),
                "credit_floor": self.floor,
            }
