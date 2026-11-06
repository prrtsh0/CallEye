"""Application configuration.

Everything configurable lives here and is read from environment variables or a
.env file. Real secrets are never committed; only .env.example is checked in.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the project (one level up from app/).
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FIXTURES_DIR = DATA_DIR / "fixtures"
STATIC_DIR = BASE_DIR / "app" / "static"
SITE_DIR = BASE_DIR / "site"                      # public landing
SHARED_DIR = STATIC_DIR / "shared"                # shared ES modules / tokens
APP_DIR = STATIC_DIR / "app"                      # installable PWA
PLAYBOOKS_DIR = BASE_DIR / "app" / "detector" / "playbooks"
MODEL_PATH = BASE_DIR / "app" / "detector" / "model.joblib"


class Settings(BaseSettings):
    """Environment-driven settings. Defaults match a clean local/mock run."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Identity -----------------------------------------------------------
    app_name: str = "CallEye"

    # Gnani --------------------------------------------------------------
    # "mock" needs no network and no key. "live" talks to Gnani Prisma.
    gnani_mode: str = "mock"
    gnani_api_key: str = ""
    gnani_stt_ws_url: str = ""
    gnani_tts_url: str = ""

    # Access & abuse controls -------------------------------------------
    invite_codes: str = ""  # comma separated; empty => live mode open
    session_max_seconds: int = 90
    daily_cap_per_device: int = 10
    global_kill_switch: bool = False  # forces mock mode
    credit_floor: float = 1000.0
    stt_credits_per_minute: float = 0.33

    # Admin / ops --------------------------------------------------------
    admin_token: str = ""
    allowed_origins: str = ""  # comma separated
    log_level: str = "info"

    # Database -----------------------------------------------------------
    # Leave empty to use local SQLite (data/calleye.db). Set to a Neon
    # Postgres DSN (postgres://…) for a managed, persistent user store.
    database_url: str = ""

    # Landing/app --------------------------------------------------------
    app_url: str = "/app/"  # single config value for the app URL (landing uses this)

    @property
    def effective_mode(self) -> str:
        """Kill switch forces mock mode regardless of gnani_mode."""
        return "mock" if self.global_kill_switch else self.gnani_mode

    @property
    def invite_code_set(self) -> set[str]:
        return {c.strip().upper() for c in self.invite_codes.split(",") if c.strip()}

    @property
    def live_enabled(self) -> bool:
        """Live mode requires gnani_mode=live AND at least one invite code."""
        return self.effective_mode == "live" and bool(self.invite_code_set)

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
