# Security & privacy review

Reviewed: the full repo as of the v1.0.0 commit. This is a ranked list of
findings; the top items are already addressed by design. Nothing here has been
"fixed" without being listed — the highest-risk items were designed out from
the start.

## Findings (ranked by risk)

1. **Gnani key exposure** — `HIGH`.
   The key is only needed server-side. The browser never receives it because all
   Gnani calls go through the `/ws/listen` relay (`app/relay.py`) and the
   adapter layer (`app/gnani/`). The render only ever sees `app/static/`.
   *Status: mitigated by design.*

2. **Audio / transcript persistence** — `HIGH`.
   Audio is streamed and never written to disk; transcripts live in memory for
   the session and are not logged. `CreditTracker` keeps numbers/counters only.
   No third-party scripts, analytics, or accounts.
   *Status: mitigated by design.*

3. **Input validation on the WebSocket** — `MEDIUM`.
   `/ws/listen` accepts a `start` JSON frame then binary audio. We validate the
   control frame, invite code, and device cap, and cap session length. Binary
   frames are passed straight to the STT adapter.
   *Remaining:* the STT adapter should reject non-audio payloads / oversized
   frames (defense-in-depth if the Gnani endpoint ever exposes it). No untrusted
   client data is ever rendered as HTML (transcripts are inserted via
   `textContent`, not innerHTML).

4. **Validation on the HTTP endpoints** — `MEDIUM`.
   `POST /api/analyze` requires non-empty `text`; `POST /api/transcribe`
   accepts an upload and pasess it to the file STT adapter. There is no upload
   size/content-type limit enforced at the app layer (host/HTTP level should
   enforce one). `/admin/usage` requires `ADMIN_TOKEN` when configured.

5. **CORS** — `LOW`. `ALLOWED_ORIGINS` is respected via an allow-list when set;
   no wildcard is used.

## Privacy commitments (from the User Guide/Handbook)

- CallEye listens only after the user taps the button; it stops after 90s or
  when stopped.
- Audio is processed live and not saved; transcripts are not stored on the
  server.
- Guardian, trusted contacts, and settings live in the device's `localStorage`.
- The guardian alert carries only the call type and time — never a transcript.
- The family safe word is never stored.

## Still to do before live use

- [ ] Enforce upload size / content-type limits on `/api/transcribe`.
- [ ] Add an audio-payload guard in the STT adapter (size/rate limits).
- [ ] Confirm Rabbit's exact wire contract and rate limits (docs/gnani-notes.md).
- [ ] Set `ADMIN_TOKEN` and `ALLOWED_ORIGINS` in the deployed environment.
