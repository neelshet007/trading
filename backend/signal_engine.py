from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from market_utils import ensure_utc, format_time_in_zone
from trading_engine import evaluate_latest_signal, resolve_market_config


def _probability_label(score: int) -> str:
    if score >= 8:
        return "High"
    if score >= 6:
        return "Medium"
    return "Low"


def _signal_payload(signal) -> Dict[str, Any]:
    direction = "bullish" if signal.direction == "long" else "bearish"
    score_total = signal.score.total
    categories = ["Trend Filter", "Momentum Filter", "ATR Volatility Filter", "Liquidity Sweep", "Price Action Confirmation"]
    timestamp = signal.timestamp.to_pydatetime() if hasattr(signal.timestamp, "to_pydatetime") else signal.timestamp

    return {
        "symbol": signal.symbol,
        "market": signal.market,
        "strategy": "Trend Pullback Liquidity Engine",
        "signal": direction,
        "score": float(score_total),
        "reasons": signal.reasons,
        "timeframe": signal.timeframe,
        "entry_zone": round(signal.entry, 4),
        "stop_loss": round(signal.stop_loss, 4),
        "target": round(signal.take_profit, 4),
        "risk_reward": round(signal.risk_reward, 2),
        "timestamp": ensure_utc(timestamp),
        "timestamp_display_ist": format_time_in_zone(timestamp, "Asia/Kolkata"),
        "patterns": [signal.confirmation_type or "price_action_confirmation"],
        "pattern_strength": float(score_total),
        "breakout_level": round(signal.liquidity_level, 4) if signal.liquidity_level is not None else None,
        "categories": categories,
        "confluence_score": float(score_total),
        "pattern_details": [
            {
                "setup_type": signal.setup_type,
                "confirmation_type": signal.confirmation_type,
                "score": signal.score.as_dict(),
                "metrics": signal.metrics,
                "liquidity_level": signal.liquidity_level,
                "sweep_level": signal.sweep_level,
                "trap_level": signal.trap_level,
            }
        ],
        "probability": {
            "breakout": _probability_label(score_total),
            "trend_continuation": _probability_label(score_total),
        },
        "analysis_summary": {
            "headline": f"{direction.title()} high-probability pullback setup",
            "explanation": "Trend, momentum, pullback, liquidity sweep, and confirmation are all aligned under the deterministic ruleset.",
            "why_now": signal.reasons[0] if signal.reasons else "Core filters aligned.",
            "rating": _probability_label(score_total),
            "categories": categories,
            "pattern_descriptions": [
                f"Confirmation: {(signal.confirmation_type or 'none').replace('_', ' ')}",
                f"Liquidity level: {round(signal.liquidity_level, 4)}" if signal.liquidity_level is not None else "Liquidity level unavailable",
            ],
            "probability": {
                "breakout": _probability_label(score_total),
                "trend_continuation": _probability_label(score_total),
            },
        },
    }


def analyze_stock(symbol: str, market: str, df: pd.DataFrame, timeframe: str) -> List[Dict[str, Any]]:
    signal = evaluate_latest_signal(symbol, market, df)
    if signal is None:
        return []

    payload = _signal_payload(signal)
    payload["timeframe"] = timeframe or resolve_market_config(market).timeframe
    return [payload]
