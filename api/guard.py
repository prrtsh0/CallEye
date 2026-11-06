"""In-memory cost and abuse guards.

No database: session caps and per-device daily caps are held in memory only.
A restart resets them (acceptable for a prototype).
"""
from __future__ import annotations

import threading
import time

from api.config import Settings


class GuardManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._device_day: dict[str, tuple[str, int]] = {}  # device -> (date, count)
        self._active_sessions: dict[int, float] = {}   # ws id -> start time

    def _today(self) -> str:
        return time.strftime("%Y-%m-%d")

    def check_invite(self, code: str | None) -> bool:
        codes = self.settings.invite_code_set
        if not codes:
            return True  # no invite codes configured => open
        return (code or "").strip().upper() in codes

    def check_device_cap(self, device_id: str) -> bool:
        if self.settings.daily_cap_per_device <= 0:
            return True
        today = self._today()
        with self._lock:
            day, count = self._device_day.get(device_id, (today, 0))
            if day != today:
                self._device_day[device_id] = (today, 0)
                return True
            return count < self.settings.daily_cap_per_device

    def record_device(self, device_id: str) -> None:
        with self._lock:
            today = self._today()
            day, count = self._device_day.get(device_id, (today, 0))
            if day != today:
                count = 0
            self._device_day[device_id] = (today, count + 1)

    def open_session(self, ws_id: int) -> None:
        with self._lock:
            self._active_sessions[ws_id] = time.time()

    def close_session(self, ws_id: int) -> None:
        with self._lock:
            self._active_sessions.pop(ws_id, None)

    def session_elapsed(self, ws_id: int) -> float:
        with self._lock:
            start = self._active_sessions.get(ws_id)
        if start is None:
            return 0.0
        return time.time() - start

    def session_over(self, ws_id: int) -> bool:
        return self.session_elapsed(ws_id) >= self.settings.session_max_seconds

    def usage(self) -> dict:
        with self._lock:
            return {
                "sessions_today": sum(
                    1 for _, (day, _) in self._device_day.items() if day == self._today()),
                "active_sessions": len(self._active_sessions),
                "session_max_seconds": self.settings.session_max_seconds,
                "daily_cap_per_device": self.settings.daily_cap_per_device,
            }
