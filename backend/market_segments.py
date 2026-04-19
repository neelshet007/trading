from __future__ import annotations

from typing import Any, Dict


CRYPTO_CORE_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
]

CRYPTO_TOP_50_SYMBOLS = [
    "XRP-USD",
    "BNB-USD",
    "DOGE-USD",
    "ADA-USD",
    "TRX-USD",
    "LINK-USD",
    "AVAX-USD",
    "DOT-USD",
    "TON11419-USD",
    "SHIB-USD",
    "SUI20947-USD",
    "HBAR-USD",
    "BCH-USD",
    "LTC-USD",
    "XLM-USD",
    "UNI7083-USD",
    "APT21794-USD",
    "NEAR-USD",
    "PEPE24478-USD",
    "ICP-USD",
    "ETC-USD",
    "AAVE-USD",
    "MKR-USD",
    "ARB11841-USD",
    "OP-USD",
    "INJ-USD",
    "FIL-USD",
    "ATOM-USD",
    "RENDER-USD",
    "TAO22974-USD",
    "SEI23149-USD",
    "FET-USD",
    "VET-USD",
    "RUNE-USD",
    "TIA22861-USD",
    "JUP29210-USD",
    "WIF-USD",
    "BONK-USD",
    "ALGO-USD",
    "IMX10603-USD",
    "STX4847-USD",
    "FLOW-USD",
    "GRT6719-USD",
    "EOS-USD",
    "THETA-USD",
    "SAND-USD",
    "MANA-USD",
]


MARKET_SEGMENTS: Dict[str, Dict[str, Any]] = {
    "crypto": {
        "slug": "crypto",
        "title": "Crypto Market Microstructure",
        "backend_market": "CRYPTO",
        "default_timeframe": "swing",
        "poll_interval_seconds": 20,
        "activation_ttl_seconds": 300,
        "margin_profile": "Convexity-aware crypto execution",
        "zoom_resolution": "4H / 1H / 15M / 5M / 1M",
        "scanner_focus": "BTC, ETH, SOL plus liquid large-cap alts with HMM regime, SMC confluence, and HITL trap detection.",
        "symbols": [*CRYPTO_CORE_SYMBOLS, *CRYPTO_TOP_50_SYMBOLS],
    }
}


def get_market_segment(segment: str) -> Dict[str, Any] | None:
    return MARKET_SEGMENTS.get(segment.strip().lower())
