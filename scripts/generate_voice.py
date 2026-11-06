"""Pre-generate Timbre TTS voice clips at build time (no runtime TTS cost).

Usage: python scripts/generate_voice.py [--live]
In mock mode (default) this writes placeholder clips so playback wiring works
without a Gnani key. With --live it calls the Timbre adapter for each phrase and
writes the real audio.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from api.config import APP_DIR, get_settings  # noqa: E402
from api.gnani import get_tts_adapter  # noqa: E402
from api.gnani.types import TTSRequest  # noqa: E402

VOICE_LINES = APP_DIR / "i18n" / "voice_lines.json"
AUDIO_DIR = APP_DIR / "audio"

_EXT = {"audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg"}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    settings.gnani_mode = "live" if args.live else "mock"
    tts = get_tts_adapter(settings)

    lines = json.loads(VOICE_LINES.read_text(encoding="utf-8"))
    manifest = {}
    for item in lines:
        lang = item["language"]
        clip_id = item["id"]
        audio = await tts.synthesize(TTSRequest(language=lang, text=item["text"]))
        ext = _EXT.get(audio.content_type, "mp3")
        rel = f"{lang}/{clip_id}.{ext}"
        out = AUDIO_DIR / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(audio.data)
        # Public URL the browser uses to fetch the clip (manifest key = "lang/level").
        manifest[f"{lang}/{clip_id}"] = f"/audio/{rel}"

    (AUDIO_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(lines)} clips -> {AUDIO_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
