"""Decision rules with hysteresis.

Levels:
  GREEN - "No warning signs so far" (never "safe")
  AMBER - "Careful. Check before you act"
  RED   - "Hang up. Your guardian has been told"

Hysteresis:
  * Red latches for the rest of the call.
  * Amber returns to green only after 20s without new signals.
"""
from __future__ import annotations

from enum import IntEnum


class Level(IntEnum):
    GREEN = 0
    AMBER = 1
    RED = 2


GREEN_TEXT = "No warning signs so far. Check the caller calmly."
AMBER_TEXT = "Careful. Check before you act."
RED_TEXT = "Hang up. Your guardian has been told."

AMBER_COOLDOWN = 20.0


class DecisionEngine:
    def __init__(self):
        self.level = Level.GREEN
        self.last_amber_t: float | None = None
        self.red_latched = False

    def _red(self) -> Level:
        self.red_latched = True
        self.level = Level.RED
        return Level.RED

    def decide(self, s, t: float) -> Level:
        """`s` carries the analysis snapshot."""
        if self.red_latched:
            self.level = Level.RED
            return Level.RED

        # Would-never ask -> straight to red.
        if getattr(s, "would_never_ask", False):
            return self._red()

        lever = getattr(s, "lever", "unknown")
        p_scam = getattr(s, "p_scam", None) or 0.5
        stages = getattr(s, "stages_hit", 0)
        pressure = getattr(s, "pressure", 0.0)
        money = getattr(s, "money_demand", False)
        isolation = getattr(s, "isolation", False)
        urgency = getattr(s, "urgency", False)

        # Emergency claims default to amber; red only if money + (isolation/urgency)
        # and the classifier is confident.
        if lever == "emergency":
            if money and (isolation or urgency) and p_scam >= 0.8:
                return self._red()
            return self._amber(t)

        # Prize/lottery scams always demand a fee -> amber.
        if lever == "reward" and money:
            return self._amber(t)

        # Classic digital-arrest pattern.
        if stages >= 3 and pressure >= 70 and p_scam >= 0.8:
            return self._red()

        # Amber decision.
        if stages >= 1 and pressure >= 40:
            if self.level != Level.AMBER:
                return self._amber(t)
            # Already amber: refresh the cooldown timer (still active).
            self.last_amber_t = t
            return Level.AMBER

        # Not enough signals -> green (unless currently amber on cooldown).
        if self.level == Level.AMBER and self.last_amber_t is not None:
            if t - self.last_amber_t < AMBER_COOLDOWN:
                return Level.AMBER
            self.last_amber_t = None
        self.level = Level.GREEN
        return Level.GREEN

    def _amber(self, t: float) -> Level:
        self.level = Level.AMBER
        self.last_amber_t = t
        return Level.AMBER

    @property
    def label(self) -> str:
        return {Level.GREEN: "green", Level.AMBER: "amber", Level.RED: "red"}[self.level]

    @property
    def screen_text(self) -> str:
        return {Level.GREEN: GREEN_TEXT, Level.AMBER: AMBER_TEXT, Level.RED: RED_TEXT}[self.level]
