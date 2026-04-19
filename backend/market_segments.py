from __future__ import annotations

from typing import Any, Dict


CRYPTO_CORE_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
]

MARKET_SEGMENTS: Dict[str, Dict[str, Any]] = {
    "crypto": {
        "slug": "crypto",
        "title": "Crypto Market Microstructure",
        "backend_market": "CRYPTO",
        "default_timeframe": "5m",
        "poll_interval_seconds": 300,
        "activation_ttl_seconds": 300,
        "margin_profile": "Convexity-aware crypto execution",
        "zoom_resolution": "4H / 1H / 15M / 5M / 1M",
        "scanner_focus": "BTC, ETH, and SOL only with 5-minute forensic refresh, HMM gating, SMC confluence, and anti-stale protection.",
        "symbols": [*CRYPTO_CORE_SYMBOLS],
    }
}


def get_market_segment(segment: str) -> Dict[str, Any] | None:
    return MARKET_SEGMENTS.get(segment.strip().lower())
