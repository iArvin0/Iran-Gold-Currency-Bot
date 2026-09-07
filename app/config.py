from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    oanor_api_key: str
    oanor_base_url: str
    cache_ttl_seconds: int
    symbols_cache_ttl_seconds: int
    http_timeout_seconds: float
    log_dir: Path
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError(
                "BOT_TOKEN is missing. Copy .env.example to .env and add your BotFather token."
            )

        oanor_api_key = os.getenv("OANOR_API_KEY", "").strip()
        if not oanor_api_key:
            raise RuntimeError(
                "OANOR_API_KEY is missing. Create a key for the Iran Rial Market API "
                "and add it to .env."
            )

        log_dir = Path(os.getenv("LOG_DIR", "logs")).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            bot_token=bot_token,
            oanor_api_key=oanor_api_key,
            oanor_base_url=os.getenv(
                "OANOR_BASE_URL",
                "https://api.oanor.com/irr-api",
            ).rstrip("/"),
            cache_ttl_seconds=_positive_int("CACHE_TTL_SECONDS", 60),
            symbols_cache_ttl_seconds=_positive_int(
                "SYMBOLS_CACHE_TTL_SECONDS",
                21600,
            ),
            http_timeout_seconds=_positive_float("HTTP_TIMEOUT_SECONDS", 15.0),
            log_dir=log_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be at least 1.")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0.")
    return value
