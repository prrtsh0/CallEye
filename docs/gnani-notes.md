# Gnani integration notes

Everything learned about Gnani's APIs lives here with its source URL, so the
adapter code can be verified against the docs on Day 1.

## Quick start

- Docs homepage: https://docs.gnani.ai/api/introduction/quick-start
- Product: **Prisma** (speech-to-text), **Timbre** (text-to-speech).

## Confirmed (from the Handbook / docs)

- Prisma has a realtime **WebSocket** API with an endpoint of the form
  `wss://api.vachana.ai/stt/v3` and an `X-API-Key-ID` header for authentication.
- Prisma v3.0 handles calls that switch between Indian languages.
- Timbre offers text-to-speech via REST with a realtime option.

## Must confirm on Day 1 (not yet verified)

- [ ] Exact audio wire format (expected: PCM16 mono 16 kHz — confirm).
- [ ] Exact message contract (start/config frame shape, transcript event shape).
- [ ] Which Prisma version the programme credits cover.
- [ ] Language codes (`hi`, `hi-latn`, `en`).
- [ ] Available Timbre voices and Marathi quality.
- [ ] Billing unit for realtime STT.
- [ ] Rate limits (pricing screen mentions 60 requests per…).
- [ ] Confirm the 0.33 credits/min STT rate; confirm programme credits convert
      the same way.

## Rules

- All Gnani code lives in `app/gnani/`. Nothing else knows a URL, header, or
  field name.
- Every feature must work in mock mode (replays `data/fixtures`), so development
  and CI use zero credits.
- Use at most two of the three free API keys: one for dev, one for the deployed
  app; keep the third spare. If a key is ever committed or shown, revoke and
  reissue.

## Current adapter status

| Feature | File | Status |
| --- | --- | --- |
| Realtime STT (WS) | `app/gnani/realtime.py` | scaffolded per contract; verify wire format |
| File STT (REST) | `app/gnani/file.py` | scaffolded per contract |
| TTS (Timbre) | `app/gnani/tts.py` | scaffolded per contract |
| Mock adapters | `app/gnani/mock.py` | complete, used by default |
