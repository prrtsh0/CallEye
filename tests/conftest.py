"""Shared fixtures. Provides an authenticated client for endpoints that now
require a user token (A1)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_EMAIL = "tester@calleye.dev"
TEST_PASS = "correct-horse-battery"  # noqa: S105  (test fixture, not a secret)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_token(client):
    """Sign up (ignore if exists) and return a valid bearer token."""
    r = client.post("/api/auth/signup", json={
        "email": TEST_EMAIL, "name": "Tester", "password": TEST_PASS,
    })
    if r.status_code == 409:
        r = client.post("/api/auth/login", json={
            "email": TEST_EMAIL, "password": TEST_PASS,
        })
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth_client(client, auth_token):
    def authed(method, url, **kw):
        headers = dict(kw.pop("headers", {}))
        headers["Authorization"] = "Bearer " + auth_token
        return client.request(method, url, headers=headers, **kw)
    return authed
