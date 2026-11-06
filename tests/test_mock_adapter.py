import asyncio

from api.config import Settings
from api.gnani import get_stt_adapter, get_tts_adapter
from api.gnani.types import TTSRequest


def test_mock_stt_streams_segments():
    s = Settings(_env_file=None, gnani_mode="mock")
    adapter = get_stt_adapter(s)
    seen = []

    async def on_segment(text, final, t):
        seen.append((text, final))

    async def go():
        agen = adapter.stream("hi", on_segment)
        while True:
            try:
                await agen.__anext__()
            except StopAsyncIteration:
                break

    asyncio.run(go())
    assert seen, "mock STT should produce segments"


def test_mock_tts_returns_bytes():
    s = Settings(_env_file=None)
    adapter = get_tts_adapter(s)
    audio = asyncio.run(adapter.synthesize(TTSRequest(language="hi", text="test")))
    assert len(audio.data) > 0
