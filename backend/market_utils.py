from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, Tuple

UTC = ZoneInfo("UTC")
IST = ZoneInfo("Asia/Kolkata")

DEFAULT_TIMEZONE = UTC

MARKET_CONFIG: Dict[str, Dict[str, Any]] = {
    "CRYPTO": {
        "timezone": UTC,
        "display_timezone": "UTC",
        "session_timezone": "UTC",
        "always_open": True,
    }
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def ist_now() -> datetime:
    return datetime.now(IST)


def ensure_utc(dt: datetime | None = None) -> datetime:
    if dt is None:
        return utc_now()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def format_time_in_zone(dt: datetime, timezone_name: str) -> str:
    local_dt = ensure_utc(dt).astimezone(ZoneInfo(timezone_name))
    return local_dt.strftime("%I:%M %p").lstrip("0")


def get_market_clock(market: str, now_utc: datetime | None = None) -> Dict[str, Any]:
    now_utc = ensure_utc(now_utc)
    config = MARKET_CONFIG.get(market, MARKET_CONFIG["CRYPTO"])
    return {
        "market": market,
        "timestamp_utc": now_utc,
        "india_time": now_utc.astimezone(IST).strftime("%I:%M %p").lstrip("0"),
        "india_label": "IST",
        "display_timezone": config["display_timezone"],
        "local_time": now_utc.astimezone(config["timezone"]).strftime("%I:%M %p").lstrip("0"),
        "local_label": config["session_timezone"],
        "phase": "open",
        "status_text": "24/7 Open",
        "status_color": "green",
        "is_open": True,
    }


def normalize_symbol(symbol: str, market: str | None = None) -> str:
    normalized = symbol.strip().upper()
    return normalized if normalized.endswith("-USD") else f"{normalized}-USD"


def candidate_symbols(symbol: str, market: str | None = None) -> Tuple[str, ...]:
    normalized = symbol.strip().upper()
    if normalized.endswith("-USD"):
        root = normalized.removesuffix("-USD")
        return (normalized, root)
    return (f"{normalized}-USD", normalized)
