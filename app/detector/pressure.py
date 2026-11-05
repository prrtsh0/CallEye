"""Pressure meter: weighted urgency/isolation/ask signals with exponential
decay (half-life ~20 s) and a short trend history."""
from __future__ import annotations

import math

from app.detector.lexicon import PlaybookLexicon

HALF_LIFE = 20.0


class PressureMeter:
    def __init__(self, half_life: float = HALF_LIFE):
        self.half_life = half_life
        self.pressure = 0.0
        self.last_t = 0.0
        self.history: list[float] = []

    def _decay(self, dt: float) -> float:
        if dt <= 0:
            return 1.0
        return math.pow(0.5, dt / self.half_life)

    def update(self, lexicon: PlaybookLexicon, text: str, t: float) -> float:
        dt = max(0.0, t - self.last_t)
        self.last_t = t
        self.pressure *= self._decay(dt)
        inc = lexicon.weighted_score("urgency", text) + \
            lexicon.weighted_score("isolation", text) + \
            lexicon.weighted_score("ask", text) * 0.5
        self.pressure = min(100.0, self.pressure + inc)
        self.history.append(round(self.pressure, 1))
        if len(self.history) > 3:
            self.history.pop(0)
        return round(self.pressure, 1)

    def trend(self) -> str:
        """'rising', 'falling', or 'flat' over the last three readings."""
        if len(self.history) < 2:
            return "flat"
        if self.history[-1] > self.history[0] + 1.0:
            return "rising"
        if self.history[-1] < self.history[0] - 1.0:
            return "falling"
        return "flat"
