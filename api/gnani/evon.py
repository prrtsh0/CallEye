"""Evon reasoning adapter (REST) and an offline mock fallback.

Evon is Gnani's 30B-parameter reasoning model. CallEye uses it to turn a raw
detector verdict into a calm, plain-language explanation in the user's language,
and to draft the guardian alert. The wire format here follows the same contract
as the other adapters: it is isolated in this file so only this one needs to be
adjusted when the exact Gnani API shape is confirmed from the docs.
"""
from __future__ import annotations

import asyncio

import httpx

from api.gnani.base import ReasonAdapter
from api.gnani.types import ReasonRequest, ReasonResponse
from model.detector.explain import build_explanation, guardian_note


class EvonReasonAdapter(ReasonAdapter):
    """Talks to the Evon model over HTTP."""

    def __init__(self, url: str, api_key: str, model: str = "evon"):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def explain(self, request: ReasonRequest) -> ReasonResponse:
        headers = {"X-API-Key-ID": self.api_key}
        payload = {
            "model": self.model,
            "language": request.language,
            "level": request.level,
            "transcript": request.transcript,
            "signals": request.reasons,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.url}/reason", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return ReasonResponse(
            explanation=data.get("explanation", ""),
            guardian_note=data.get("guardian_note", ""),
        )


class MockReasonAdapter(ReasonAdapter):
    """Deterministic, offline explanation (zero cost, used in mock/CI)."""

    async def explain(self, request: ReasonRequest) -> ReasonResponse:
        await asyncio.sleep(0.001)
        proxy = type("Proxy", (), {
            "level": request.level,
            "reasons": request.reasons,
        })()
        return ReasonResponse(
            explanation=build_explanation(proxy),
            guardian_note=guardian_note(proxy),
        )
