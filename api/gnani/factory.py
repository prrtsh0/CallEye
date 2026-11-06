"""Factory that returns the right adapters for the current mode."""
from __future__ import annotations

from api.config import Settings
from api.gnani.base import ReasonAdapter, STTAdapter, TTSAdapter
from api.gnani.evon import EvonReasonAdapter, MockReasonAdapter
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
            api_base=settings.gnani_stt_ws_url,
            api_key=settings.gnani_api_key,
        )
    # In mock mode the mock adapter also handles file transcription.
    return MockSTTAdapter(settings)


def get_tts_adapter(settings: Settings) -> TTSAdapter:
    if settings.effective_mode == "live" and settings.gnani_tts_url:
        return TimbreTTSAdapter(url=settings.gnani_tts_url, api_key=settings.gnani_api_key)
    return MockTTSAdapter()


def get_reason_adapter(settings: Settings) -> ReasonAdapter:
    """Evon reasoning adapter in live mode; deterministic rule-based mock otherwise."""
    if settings.effective_mode == "live" and settings.gnani_evon_url:
        return EvonReasonAdapter(
            url=settings.gnani_evon_url,
            api_key=settings.gnani_evon_api_key or settings.gnani_api_key,
            model=settings.gnani_evon_model,
        )
    return MockReasonAdapter()
