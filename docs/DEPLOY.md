# Deployment

This project is a Dockerized FastAPI service. It can run on Render (recommended)
or Hugging Face Spaces.

## Build & run locally

```bash
docker build -t calleye .
docker run -p 8000:8000 -e GNANI_MODE=mock calleye
```

Health check: `GET /healthz` → `{"status":"ok",...}`.

## Render (recommended)

1. Push this repo to GitHub.
2. In Render choose **New → Web Service**, connect the repo.
3. Runtime: **Docker**.
4. Health check path: `/healthz`.
5. Add environment variables from `.env.example` (section 5 of the Handbook).
   Start with `GNANI_MODE=mock` to verify the deploy, then switch to live with
   your deploy key.
6. Deploy, open the HTTPS URL, then test `/mic-test` and a practice call on a
   real phone.

Notes:

- Free web services usually sleep when idle and take a while to wake. Wake the
  service before every demo; consider a paid instance for the demo window.
- Rollback: redeploy the previous commit.

## Hugging Face Spaces (alternative)

1. Create a **Docker Space**.
2. Set `app_port` to match the port the container listens on (default 8000).
3. Add secrets in the Space settings (the env vars from `.env.example`).

## Environment variables

| Var | Purpose |
| --- | --- |
| `GNANI_MODE` | `mock` (default) or `live` |
| `GNANI_API_KEY` | Gnani API key (never commit) |
| `GNANI_STT_WS_URL` | Prisma realtime STT WS endpoint |
| `GNANI_TTS_URL` | Timbre TTS endpoint |
| `INVITE_CODES` | comma-separated codes for live mode |
| `SESSION_MAX_SECONDS` | default 90 |
| `DAILY_CAP_PER_DEVICE` | default 10 |
| `GLOBAL_KILL_SWITCH` | `1` forces mock mode |
| `CREDIT_FLOOR` / `STT_CREDITS_PER_MINUTE` | credit guards |
| `ADMIN_TOKEN` | protects `/admin/usage` |
| `ALLOWED_ORIGINS` | CORS allow-list |

## Pre-demo checklist

- [ ] Wake the service
- [ ] `python scripts/smoke.py https://your-app-url` passes
- [ ] One live call end-to-end works
- [ ] `/admin/usage` shows sane numbers
- [ ] Kill switch off, credits above floor
- [ ] Charge both devices; put them in Do Not Disturb
