"""Factory that returns the right adapters for the current mode."""
from __future__ import annotations

from api.config import Settings
from api.gnani.base import STTAdapter, TTSAdapter
from api.gnani.file import FileSTTAdapter
from api.gnani.mock import MockSTTAdapter, MockTTSAdapter
from api.gnani.realtime import RealtimeSTTAdapter
from api.gnani.tts import TimbreTTSAdapter


def get_stt_adapter(settings: Settings) -> STTAdapter:
    if settings.effective_mode == "live" and settings.gnani_stt_ws_url:
        return RealtimeSTTAdapter(
            ws_url=settings.gnani_stt_ws_url,
            api_key=settings.gnani_api_key,
        )
    return MockSTTAdapter(settings)


def get_file_stt_adapter(settings: Settings) -> STTAdapter:
    if settings.effective_mode == "live" and settings.gnani_stt_ws_url:
        return FileSTTAdapter(
            api_base=settings.gnani_stt_ws_url, api_key=settings.gnani_api_key)
    # In mock mode the mock adapter also handles file transcription.
    return MockSTTAdapter(settings)


def get_tts_adapter(settings: Settings) -> TTSAdapter:
    if settings.effective_mode == "live" and settings.gnani_tts_url:
        return TimbreTTSAdapter(url=settings.gnani_tts_url, api_key=settings.gnani_api_key)
    return MockTTSAdapter()
