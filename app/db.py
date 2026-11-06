"""User + session store.

Defaults to SQLite (stdlib, zero extra deps) at data/calleye.db. If
DATABASE_URL is set (e.g. a Neon Postgres DSN), a managed Postgres is used
instead, so user accounts persist across deploy/restart cycles.

Passwords are never stored in plaintext — only PBKDF2-SHA256 hashes with a
per-user salt (see app/auth.py).
"""
from __future__ import annotations

import sqlite3

from app.config import DATA_DIR, get_settings

DB_PATH = DATA_DIR / "calleye.db"
_settings = get_settings()


def _pg_dsn() -> str:
    return _settings.database_url.strip()


def backend_name() -> str:
    return "postgres" if _pg_dsn() else "sqlite"


# --- schema (both backends, same logical tables) ---------------------------
_USERS_DDL_SQLITE = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
"""
_SESSIONS_DDL_SQLITE = """
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
"""
_USERS_DDL_PG = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
"""
_SESSIONS_DDL_PG = """
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
"""


def get_connection():
    dsn = _pg_dsn()
    if dsn:
        import psycopg  # noqa: PLC0415  (lazy: SQLite path needs no extra dep)

        return psycopg.connect(dsn, row_factory=psycopg.rows.dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    dsn = _pg_dsn()
    if dsn:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_USERS_DDL_PG)
                cur.execute(_SESSIONS_DDL_PG)
            conn.commit()
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(_USERS_DDL_SQLITE)
        conn.execute(_SESSIONS_DDL_SQLITE)
        conn.commit()
