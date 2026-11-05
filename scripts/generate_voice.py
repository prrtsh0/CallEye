"""Pre-generate Timbre TTS voice clips at build time (no runtime TTS cost).

Usage: python scripts/generate_voice.py [--live]
In mock mode (default) this writes placeholder clips so playback wiring works
without a Gnani key. With --live it calls the Timbre adapter for each phrase.
"""
from __future__ import annotations

import argparse
import hashlib
import json

from app.config import STATIC_DIR, get_settings
from app.gnani import get_tts_adapter
from app.gnani.types import TTSRequest

VOICE_LINES = STATIC_DIR / "i18n" / "voice_lines.json"
AUDIO_DIR = STATIC_DIR / "audio"


def main() -> None:
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
        out = AUDIO_DIR / lang / f"{clip_id}.mp3"
        out.parent.mkdir(parents=True, exist_ok=True)
        audio = tts.synthesize(TTSRequest(language=lang, text=item["text"]))
        out.write_bytes(audio.data)
        manifest[f"{lang}/{clip_id}"] = hashlib.sha256(audio.data).hexdigest()

    (AUDIO_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(lines)} clips -> {AUDIO_DIR}")


if __name__ == "__main__":
    main()
