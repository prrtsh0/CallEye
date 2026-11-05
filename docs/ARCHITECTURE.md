# Architecture

## Data flow (realtime)

```
 Browser (PWA)              FastAPI server                Gnani
 ┌────────────────┐   /ws/listen   ┌─────────────────────┐   ┌──────────┐
 │ getUserMedia mic │──▶ audio ───▶│ relay.py (key held  │──▶│ Prisma   │
 │ AudioWorklet 16k │              │  here — never in    │   │ STT      │
 │ live transcript   │◀── JSON ────│  browser)           │◀──│ (WS)     │
 │ Pressure Meter     │              │ detector.analyze_   │   └──────────┘
 │ colour verdict     │              │  update()           │
 └──────────────────┘              └─────────────────────┘
```

- **Browser** captures mic audio via `getUserMedia` and downsamples to PCM16
  mono 16 kHz in an `AudioWorklet`, sending binary frames over `/ws/listen`.
- **Relay** validates invite code + device cap, forwards frames to the STT
  adapter, and streams JSON events back (transcript, analysis, budget, error).
- **Detector** keeps per-session state (transcript, pressure, stages, decision)
  and produces the verdict.
- **Gnani adapter** is isolated in `app/gnani/`; a mock replays recorded
  fixtures for zero-cost development/CI.

## HTTP API

| Endpoint | Purpose |
| --- | --- |
| `GET /healthz` | host health check |
| `GET /api/config` | languages, limits, live/mock mode |
| `POST /api/analyze` | text → verdict (tests, upload mode) |
| `POST /api/transcribe` | audio file → STT → verdict |
| `WS /ws/listen` | realtime listening |
| `GET /admin/usage` | counters + credit estimate (needs `ADMIN_TOKEN`) |
| `GET /mic-test` | microphone test page |

## Cost & abuse guards

- session time cap, per-device daily cap (in memory), invite codes for live
  mode, global kill switch → mock, credit floor, numbers-only usage log.
- Pre-generated TTS clips mean no runtime TTS cost.

## Privacy

- Audio is streamed, never written to disk; transcripts are in memory for the
  session and not logged.
- Guardians/contacts/settings live in the device's `localStorage` only; the
  family safe word is never stored.
- No analytics, no third-party scripts, no accounts.

## Detector

See [DETECTOR.md](DETECTOR.md) for the full rule specification.
