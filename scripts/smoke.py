"""Smoke test against a deployed/local URL.

Usage: python scripts/smoke.py http://localhost:8000
Checks /healthz and /api/config, then opens a WebSocket session and expects a
transcript event (mock mode streams one without needing audio).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from urllib.parse import urlparse

import httpx
import websockets


async def check_ws(base: str) -> None:
    parsed = urlparse(base)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{scheme}://{parsed.netloc}/ws/listen"

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "type": "start", "lang": "hi", "code": "", "device_id": "smoke-1"}))
        seen_transcript = False
        deadline = asyncio.get_event_loop().time() + 20
        while asyncio.get_event_loop().time() < deadline:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            if msg.get("type") == "transcript":
                seen_transcript = True
                print(f"  transcript: {msg.get('text','')[:60]}")
            if msg.get("type") == "analysis":
                print(f"  analysis level: {msg.get('level')}")
            if seen_transcript:
                break
        await ws.send(json.dumps({"type": "stop"}))
        if not seen_transcript:
            raise RuntimeError("no transcript event received")


async def smoke(base: str) -> None:
    print(f"Smoke testing {base}")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base.rstrip('/')}/healthz")
        r.raise_for_status()
        print("  /healthz:", r.json())
        c = await client.get(f"{base.rstrip('/')}/api/config")
        c.raise_for_status()
        print("  /api/config:", c.json())
    await check_ws(base)
    print("Smoke test OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", nargs="?", default="http://localhost:8000")
    args = parser.parse_args()
    try:
        asyncio.run(smoke(args.base))
    except Exception as exc:
        print(f"Smoke test FAILED: {exc}")
        sys.exit(1)
