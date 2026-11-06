# Deployment

CallEye is a Dockerized FastAPI service deployed on **Render** (recommended) via
a blueprint. The model is trained **during the Docker build**, so every deploy
ships a working classifier.

## Build & run locally

```bash
docker build -t calleye .
docker run -p 8000:8000 -e GNANI_MODE=mock calleye
```

Health check: `GET /healthz` → `{"status":"ok",...}`.

## Render (recommended) — Blueprint

1. Push this repo to GitHub.
2. In Render choose **New → Blueprint** (not "Web Service"), connect your repo.
3. Render reads `render.yaml` automatically. Click **Apply**.
4. On the first apply, Render prompts for the `sync: false` env vars
   (`GNANI_API_KEY`, `GNANI_STT_WS_URL`, `GNANI_TTS_URL`).
5. Deploy, open the HTTPS URL, then test `/healthz`, the landing page, and a
   practice call.

Notes:

- Free web services usually sleep when idle and take a while to wake. Wake the
  service before every demo; consider a paid instance for the demo window.
- Rollback: redeploy the previous commit.
- The Docker build runs `python -m eval.train`, producing `model.joblib` from
  the committed `data/calls` — so a fresh deploy always has a trained model.

## Automatic retraining (GitHub Actions)

`.github/workflows/train.yml` retrains and re-evaluates whenever
`data/calls/**` or `app/detector/**` change (or on manual `workflow_dispatch`):

1. Add labeled transcripts to `data/calls/train.json` (scam/genuine).
2. Push to `main`.
3. The workflow trains, evaluates on `test.json`, and commits the updated
   `eval/model_report.md`. That push redeploys Render, which retrains in the
   build. Loop closed.

## Hugging Face Spaces (alternative)

1. Create a **Docker Space**.
2. Set `app_port` to match the port the container listens on (default 8000).
3. Add secrets in the Space settings (the env vars from `.env.example`).

## Environment variables

Set these in the Render dashboard (**Service → Environment**) or via `.env` for
local runs. Secrets are never committed.

| Var | Purpose |
| --- | --- |
| `GNANI_MODE` | `mock` (default) or `live` |
| `GNANI_API_KEY` | Gnani API key (secret — never commit) |
| `GNANI_STT_WS_URL` | Prisma realtime STT WS endpoint (secret) |
| `GNANI_TTS_URL` | Timbre TTS endpoint (secret) |
| `INVITE_CODES` | comma-separated codes for live mode |
| `SESSION_MAX_SECONDS` | default 90 |
| `DAILY_CAP_PER_DEVICE` | default 10 |
| `GLOBAL_KILL_SWITCH` | `1` forces mock mode |
| `CREDIT_FLOOR` / `STT_CREDITS_PER_MINUTE` | credit guards |
| `ADMIN_TOKEN` | protects `/admin/usage` |
| `ALLOWED_ORIGINS` | CORS allow-list |

> ⚠️ Until `GNANI_MODE=live` **and** `GNANI_STT_WS_URL` are set, the app stays
> in **mock** mode (zero STT credits, replays fixtures). Flip to live only when
> you have real Gnani credentials configured in the dashboard.

## Pre-demo checklist

- [ ] Wake the service
- [ ] `python scripts/smoke.py https://your-app-url` passes
- [ ] One live call end-to-end works
- [ ] `/admin/usage` shows sane numbers
- [ ] Kill switch off, credits above floor
- [ ] Charge both devices; put them in Do Not Disturb
