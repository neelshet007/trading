from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Any, Dict, Tuple

IST = ZoneInfo("Asia/Kolkata")
US_EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

DEFAULT_TIMEZONE = IST

MARKET_CONFIG: Dict[str, Dict[str, Any]] = {
    "INDIA": {
        "timezone": IST,
        "display_timezone": "Asia/Kolkata",
        "session_timezone": "IST",
        "open_time": time(9, 15),
        "close_time": time(15, 30),
    },
    "USA": {
        "timezone": US_EASTERN,
        "display_timezone": "America/New_York",
        "session_timezone": "ET",
        "open_time": time(9, 30),
        "close_time": time(16, 0),
    },
    "CRYPTO": {
        "timezone": UTC,
        "display_timezone": "UTC",
        "session_timezone": "UTC",
        "always_open": True,
    },
    "COMMODITIES": {
        "timezone": US_EASTERN,
        "display_timezone": "America/New_York",
        "session_timezone": "ET",
        "open_time": time(9, 0),
        "close_time": time(17, 0),
    },
}

INDIA_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"


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
    config = MARKET_CONFIG.get(market, MARKET_CONFIG["INDIA"])

    india_now = now_utc.astimezone(IST)
    payload: Dict[str, Any] = {
        "market": market,
        "timestamp_utc": now_utc,
        "india_time": india_now.strftime("%I:%M %p").lstrip("0"),
        "india_label": "IST",
        "display_timezone": config["display_timezone"],
    }

    if config.get("always_open"):
        payload.update(
            {
                "local_time": now_utc.astimezone(config["timezone"]).strftime("%I:%M %p").lstrip("0"),
                "local_label": config["session_timezone"],
                "phase": "open",
                "status_text": "Market Open",
                "status_color": "green",
                "is_open": True,
            }
        )
        return payload

    local_now = now_utc.astimezone(config["timezone"])
    is_weekday = local_now.weekday() < 5
    open_time = config["open_time"]
    close_time = config["close_time"]

    if not is_weekday:
        phase = "closed"
    elif local_now.time() < open_time:
        phase = "extended"
    elif local_now.time() <= close_time:
        phase = "open"
    else:
        phase = "extended"

    status_map = {
        "open": ("Market Open", "green", True),
        "closed": ("Market Closed", "red", False),
        "extended": ("Pre-market / After-hours", "yellow", False),
    }
    status_text, status_color, is_open = status_map[phase]

    payload.update(
        {
            "local_time": local_now.strftime("%I:%M %p").lstrip("0"),
            "local_label": config["session_timezone"],
            "phase": phase,
            "status_text": status_text,
            "status_color": status_color,
            "is_open": is_open,
        }
    )
    return payload


def normalize_symbol(symbol: str, market: str | None = None) -> str:
    base = symbol.strip().upper()
    if market == "INDIA":
        if base.startswith("^"):
            return base
        if base.endswith(INDIA_SUFFIX) or base.endswith(BSE_SUFFIX):
            return base
        return f"{base}{INDIA_SUFFIX}"
    return base


def candidate_symbols(symbol: str, market: str | None = None) -> Tuple[str, ...]:
    base = symbol.strip().upper()
    if market == "INDIA":
        if base.endswith(INDIA_SUFFIX):
            root = base.removesuffix(INDIA_SUFFIX)
            return (base, f"{root}{BSE_SUFFIX}", root)
        if base.endswith(BSE_SUFFIX):
            root = base.removesuffix(BSE_SUFFIX)
            return (base, f"{root}{INDIA_SUFFIX}", root)
        return (base, f"{base}{INDIA_SUFFIX}", f"{base}{BSE_SUFFIX}")
    return (base,)
