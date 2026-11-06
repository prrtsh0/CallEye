"""Tiny SQLite-backed store for users and auth sessions.

Kept dependency-free (stdlib sqlite3) so the app runs with zero extra installs.
The database file lives at data/calleye.db and is git-ignored. Passwords are
never stored in plaintext — only PBKDF2-SHA256 hashes with a per-user salt.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "calleye.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
