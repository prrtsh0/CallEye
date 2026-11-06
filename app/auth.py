"""Authentication: password hashing, session token issue/verify, FastAPI guard.

Uses only the standard library (hashlib, secrets, sqlite3). Tokens are
opaque random strings stored in the `sessions` table so they can be revoked
and survive restarts. A protected endpoint calls `require_user`.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3

from fastapi import Depends, Header, HTTPException

from app.db import get_connection

_PBKDF2_ITERATIONS = 200_000


# ---- password hashing (PBKDF2-SHA256, per-user salt) ----
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, expected = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(dk.hex(), expected)
    except (ValueError, TypeError):
        return False


# ---- user + session helpers ----
def user_by_email(email: str):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def create_user(email: str, name: str, password: str):
    hashed = hash_password(password)
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                (email.strip().lower(), name.strip(), hashed))
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)",
                     (token, user_id))
        conn.commit()
    return token


def revoke_token(token: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def user_by_token(token: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ?", (token,)).fetchone()
        return dict(row) if row else None


# ---- FastAPI dependency ----
def require_user(authorization: str = Header(default="")) -> dict:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    user = user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    return user
