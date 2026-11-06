"""User + session store.

Defaults to SQLite (stdlib, zero extra deps) at data/calleye.db. If
DATABASE_URL is set (e.g. a Neon Postgres DSN), a managed Postgres is used
instead via psycopg_pool, so user accounts persist across deploy/restart and
survive serverless cold starts (connections are pooled + retried).

Passwords are never stored in plaintext — only PBKDF2-SHA256 hashes with a
per-user salt (see app/auth.py).
"""
from __future__ import annotations

import sqlite3
import time

from api.config import DATA_DIR, get_settings

DB_PATH = DATA_DIR / "calleye.db"
_settings = get_settings()

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


def _pg_dsn() -> str:
    return _settings.database_url.strip()


def backend_name() -> str:
    return "postgres" if _pg_dsn() else "sqlite"


# --- Postgres connection pool (serverless-friendly) ------------------------
_STATE = {"pool": None}


def _open_pool():
    """Create a psycopg_pool with a warm-up check and retry (Neon cold
    starts can suspend the DB; the first connection may need a retry)."""
    # Imported lazily so SQLite-only installs need no psycopg.
    try:
        from psycopg import rows  # noqa: PLC0415
        from psycopg_pool import ConnectionPool  # noqa: PLC0415
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "DATABASE_URL is set but psycopg-pool is not installed"
        ) from e

    last: Exception | None = None
    for attempt in range(4):
        pool = None
        try:
            pool = ConnectionPool(
                _pg_dsn(),
                min_size=0,
                max_size=5,
                timeout=8,
                open=True,
                kwargs={"connect_timeout": 15, "row_factory": rows.dict_row},
            )
            # Warm-up: acquire a connection to confirm the DB is awake.
            conn = pool.connection()
            pool.return_connection(conn)
            return pool
        except Exception as err:
            last = err
            if pool is not None:
                try:
                    pool.close()
                except Exception:  # pragma: no cover
                    pass
            time.sleep(0.5 * (attempt + 1))
    raise last if last is not None else RuntimeError("could not connect to database")


def _acquire(pool):
    last: Exception | None = None
    for attempt in range(4):
        try:
            return pool.connection()
        except Exception as err:
            last = err
            time.sleep(0.5 * (attempt + 1))
    raise last if last is not None else RuntimeError("could not acquire database connection")


class _PGConn:
    """Proxies a pooled psycopg connection so callers that use SQLite-style
    '?' placeholders work unchanged on Postgres (psycopg uses '%s'). Releases
    the pooled connection back on context exit, mirroring sqlite3.Connection."""

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def execute(self, sql, params=None):
        return self._conn.execute(sql.replace("?", "%s"), params)

    def executemany(self, sql, seq_of_params):
        return self._conn.executemany(sql.replace("?", "%s"), seq_of_params)

    def fetchone(self):
        return self._conn.fetchone()

    def fetchall(self):
        return self._conn.fetchall()

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
            self._pool.return_connection(self._conn)


def get_connection():
    dsn = _pg_dsn()
    if dsn:
        if _STATE["pool"] is None:
            _STATE["pool"] = _open_pool()
        pool = _STATE["pool"]
        return _PGConn(pool, _acquire(pool))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    if _pg_dsn():
        with get_connection() as conn:
            conn.execute(_USERS_DDL_PG)
            conn.execute(_SESSIONS_DDL_PG)
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(_USERS_DDL_SQLITE)
        conn.execute(_SESSIONS_DDL_SQLITE)
