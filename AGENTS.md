# Project instructions — CallEye

For AI coding assistants working in this repository.

## What CallEye is

A realtime pressure-call reader. It listens to speakerphone audio, transcribes
it with Gnani Prisma, scores scam risk with a hybrid detector, shows a calm
three-level result (green / amber / red), and on red alerts a guardian. It is a
prototype for a student challenge.

- Always read the app name from `APP_NAME` in `app/config.py` (default
  "CallEye"). Do not hardcode alternate names.
- Read `docs/DETECTOR.md` (detector spec) and the Engineering Handbook in
  `docs/CallEye_Engineering_Handbook.docx` before changing detection logic.

## Architecture in one paragraph

Browser (PWA) captures mic audio via `getUserMedia` and downsamples to PCM16
mono 16 kHz in an `AudioWorklet`, sending binary frames over the `/ws/listen`
WebSocket. The FastAPI relay validates invite codes and device caps, forwards
audio to a Gnani STT adapter, and streams JSON events back (transcript,
analysis, budget, error). The detector keeps per-session state and produces the
verdict.

## Layout

```
api/
  main.py            FastAPI app (HTTP, static, admin)
  relay.py           /ws/listen WebSocket relay
  config.py          pydantic-settings, .env.example
  auth.py db.py      user store + sessions (SQLite or Neon Postgres)
  guard.py           guardian alerts
  gnani/             ALL Gnani code (mock + real adapters). Nothing else may
                     know a Gnani URL, header, or field name.
model/
  detector/          normalize, lexicon, stages, pressure, asks, levers,
                     classifier, decision, engine; playbooks/ (YAML)
  eval/              train.py (model git-ignored) + run.py → reports
web/                 installable PWA (index.html, app.js, styles.css,
                     audio-processor.js, mic-test.html, manifest, sw)
landing/             public landing (index.html, docs.html, assets)
shared/              shared CSS/JS modules used by web + landing
data/
  calls/             labeled scripted-call splits (train.json, test.json)
  fixtures/          recorded transcripts for mock mode
scripts/
  generate_voice.py  pre-build TTS voice clips (Timbre / mock)
  smoke.py           deployment smoke test
tests/               pytest suite
```

## Hard rules

- **Gnani isolation:** all Gnani specifics (endpoints, headers, fields) live in
  `api/gnani/`. The Gnani key must never reach the browser. If a change invents
  a Gnani endpoint/header/field, send it back to `api/gnani/`.
- **Mock mode first:** every feature must work in mock mode
  (`GNANI_MODE=mock`), which replays `data/fixtures`. Development and CI use
  zero credits.
- **No secrets:** never commit a real `.env`. Commit only `.env.example`.
  Keep `model/detector/model.joblib` git-ignored.
- **Never tune on the test split:** the training script only reads
  `data/calls/train.json`; the test split must never influence the classifier.
- **Honesty:** never claim certainty. Green means "no warning signs so far",
  never "safe". Public posts must say "hybrid rule and ML detector evaluated on
  N scripted calls" — never "trained scam AI".

## Environment

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
uvicorn api.main:app --reload          # http://localhost:8000
```

Check:

```bash
pytest -q
python -m model.eval.run --split test
ruff check .
python scripts/smoke.py http://localhost:8000
```

## Commit style

`type: summary` — types: `feat`, `fix`, `test`, `docs`, `chore`.
Default branch `main`, tag `v1.0.0` for submission.
