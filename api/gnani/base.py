"""Abstract adapters. Everything else in the app depends only on these."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable

from api.gnani.types import TTSAudio, TTSRequest

# A callback receiving each live transcript segment as it is produced.
OnSegment = Callable[[str, bool, float], None]


class STTAdapter(ABC):
    """Speech-to-text. Live streaming or whole-file."""

    @abstractmethod
    async def transcribe_file(self, audio: bytes, language: str, **kw):
        """Transcribe a complete audio file (REST mode). Returns STTResult."""
        raise NotImplementedError

    def stream(
        self,
        language: str,
        on_segment: OnSegment,
        sample_rate: int = 16000,
        on_state: Callable[[str], None] | None = None,
    ) -> AsyncIterator[None]:
        """Open a streaming STT session.

        Feed audio frames by sending bytes into the returned async generator;
        the adapter calls ``on_segment`` whenever a (partial or final) transcript
        becomes available. Yields control back between frames.
        """
        raise NotImplementedError


class TTSAdapter(ABC):
    """Text-to-speech."""

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSAudio:
        raise NotImplementedError
