"""Gnani integration layer.

All Gnani-specific knowledge (URLs, headers, field names, wire formats) lives
inside this package and nowhere else. The rest of the app talks only to the
abstract adapters and mock/real implementations exposed here.
"""
from api.gnani.base import STTAdapter, TTSAdapter
from api.gnani.factory import get_stt_adapter, get_tts_adapter
from api.gnani.types import STTResult, TranscriptSegment, TTSAudio, TTSRequest

__all__ = [
    "STTAdapter",
    "STTResult",
    "TTSAdapter",
    "TTSAudio",
    "TTSRequest",
    "TranscriptSegment",
    "get_stt_adapter",
    "get_tts_adapter",
]
