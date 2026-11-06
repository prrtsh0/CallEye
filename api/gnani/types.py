"""Shared data types for the Gnani adapter layer."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TranscriptSegment:
    """A single speech-to-text segment."""

    text: str
    final: bool = True
    t: float = 0.0  # seconds from the start of the session


@dataclass
class STTResult:
    """Whole-file transcription result (REST upload mode)."""

    segments: list[TranscriptSegment] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return " ".join(s.text for s in self.segments).strip()


@dataclass
class TTSRequest:
    """A text-to-speech request."""

    language: str
    text: str
    voice: str | None = None


@dataclass
class TTSAudio:
    """Generated speech audio."""

    data: bytes
    content_type: str = "audio/mpeg"


@dataclass
class ReasonRequest:
    """A request to the Evon reasoning model."""

    language: str
    transcript: str
    level: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class ReasonResponse:
    """Plain-language reasoning output."""

    explanation: str
    guardian_note: str = ""
