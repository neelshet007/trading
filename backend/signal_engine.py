from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from indicators import add_indicators
from market_utils import ensure_utc, format_time_in_zone
from strategies import (
    evaluate_breakout,
    evaluate_pullback,
    evaluate_reversal,
    evaluate_trend_continuation,
)


STRATEGY_CATEGORY_MAP = {
    "Trend Continuation": "Momentum Scanner",
    "Pullback Setup": "Momentum Scanner",
    "Breakout Scanner": "Volume Spike Scanner",
    "Reversal": "Momentum Scanner",
    "VCP Scanner": "VCP Scanner",
    "Rocket Base Scanner": "Rocket Base Scanner",
    "High Confluence": "Momentum Scanner",
}

TOP_SIGNAL_LIMIT = 10


def _safe_ratio(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _latest_range(df: pd.DataFrame) -> pd.Series:
    return (df["High"] - df["Low"]).tail(10)


def detect_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    patterns: List[Dict[str, Any]] = []
    if len(df) < 30 or "Volume" not in df.columns:
        return patterns

    recent = df.tail(25).copy()
    recent["range"] = recent["High"] - recent["Low"]

    contraction_windows = [recent["range"].iloc[-20:-15], recent["range"].iloc[-15:-10], recent["range"].iloc[-10:-5]]
    avg_ranges = [window.mean() for window in contraction_windows if not window.empty]
    avg_volumes = [
        recent["Volume"].iloc[-20:-15].mean(),
        recent["Volume"].iloc[-15:-10].mean(),
        recent["Volume"].iloc[-10:-5].mean(),
    ]

    if len(avg_ranges) == 3:
        has_range_contraction = avg_ranges[0] > avg_ranges[1] > avg_ranges[2]
        has_volume_contraction = avg_volumes[0] >= avg_volumes[1] >= avg_volumes[2]
        recent_high = recent["High"].iloc[-20:-1].max()
        tight_close = _safe_ratio(recent["range"].iloc[-3:].mean(), recent["Close"].iloc[-3:].mean())
        if has_range_contraction and has_volume_contraction and tight_close < 0.035:
            strength = min(10.0, 6.5 + (avg_ranges[0] - avg_ranges[2]) / max(avg_ranges[0], 1e-9) * 3.0)
            patterns.append(
                {
                    "name": "VCP",
                    "strength": round(strength, 1),
                    "breakout_level": round(recent_high, 2),
                    "description": "Price swings are getting tighter while volume cools down. That often means sellers are losing pressure before a possible breakout.",
                }
            )

    impulse_gain = _safe_ratio(recent["Close"].iloc[-8] - recent["Close"].iloc[-20], recent["Close"].iloc[-20])
    base_range = _safe_ratio(recent["High"].iloc[-7:].max() - recent["Low"].iloc[-7:].min(), recent["Close"].iloc[-1])
    breakout_reference = recent["High"].iloc[-7:].max()
    if impulse_gain > 0.08 and base_range < 0.05 and recent["Close"].iloc[-1] >= recent["EMA_20"].iloc[-1]:
        strength = min(10.0, 6.0 + (impulse_gain * 20))
        patterns.append(
            {
                "name": "RocketBase",
                "strength": round(strength, 1),
                "breakout_level": round(breakout_reference, 2),
                "description": "The stock made a strong move, then paused in a small range. If buyers return, it can quickly resume higher.",
            }
        )

    return patterns


def _probability_label(score: float) -> str:
    if score >= 8.5:
        return "High"
    if score >= 7.0:
        return "Medium"
    return "Low"


def _build_analysis_summary(signal_type: str, score: float, categories: List[str], pattern_details: List[Dict[str, Any]], reasons: List[str]) -> Dict[str, Any]:
    direction_text = "bullish" if signal_type == "bullish" else "bearish"
    pattern_descriptions = [f"{pattern['name']} ({'Strong' if pattern['strength'] >= 8 else 'Developing'})" for pattern in pattern_details]
    headline = f"{direction_text.title()} setup with {len(categories)} active scanner{'s' if len(categories) != 1 else ''}"
    why_now = reasons[0] if reasons else "Price and volume are lining up for a fresh move."
    explanation = (
        f"This stock is important right now because it is showing fresh {direction_text} pressure with "
        f"{', '.join(categories[:3])} support."
    )
    return {
        "headline": headline,
        "explanation": explanation,
        "why_now": why_now,
        "rating": _probability_label(score),
        "categories": categories,
        "pattern_descriptions": pattern_descriptions,
        "probability": {
            "breakout": _probability_label(score + (0.4 * len(pattern_details))),
            "trend_continuation": _probability_label(score + (0.2 if signal_type == "bullish" else 0.0)),
        },
    }


def _build_signal(
    *,
    symbol: str,
    market: str,
    strategy: str,
    signal_type: str,
    score: float,
    reasons: List[str],
    timeframe: str,
    current_price: float,
    atr: float,
    timestamp: pd.Timestamp,
    patterns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    categories = sorted({STRATEGY_CATEGORY_MAP.get(strategy, strategy)})
    pattern_names = [pattern["name"] for pattern in patterns]
    strongest_pattern = max((pattern["strength"] for pattern in patterns), default=0.0)
    breakout_level = max((pattern["breakout_level"] for pattern in patterns), default=current_price)
    confluence_score = round(score + (0.35 * len(pattern_names)) + (0.25 * len(categories)), 2)

    if signal_type == "bullish":
        stop_loss = current_price - (1.5 * atr)
        target = current_price + (3.0 * atr)
    else:
        stop_loss = current_price + (1.5 * atr)
        target = current_price - (3.0 * atr)

    summary = _build_analysis_summary(signal_type, confluence_score, categories, patterns, reasons)

    return {
        "symbol": symbol,
        "market": market,
        "strategy": strategy,
        "signal": signal_type,
        "score": round(score, 1),
        "reasons": reasons,
        "timeframe": timeframe,
        "entry_zone": round(current_price, 2),
        "stop_loss": round(stop_loss, 2),
        "target": round(target, 2),
        "risk_reward": 2.0,
        "timestamp": ensure_utc(timestamp.to_pydatetime()),
        "timestamp_display_ist": format_time_in_zone(timestamp.to_pydatetime(), "Asia/Kolkata"),
        "patterns": pattern_names,
        "pattern_strength": round(strongest_pattern, 1) if strongest_pattern else None,
        "breakout_level": round(breakout_level, 2),
        "categories": categories,
        "confluence_score": confluence_score,
        "pattern_details": patterns,
        "probability": summary["probability"],
        "analysis_summary": summary,
    }


def _add_pattern_scanners(base_signals: List[Dict[str, Any]], patterns: List[Dict[str, Any]], symbol: str, market: str, timeframe: str, current_price: float, atr: float, timestamp: pd.Timestamp) -> List[Dict[str, Any]]:
    extra_signals: List[Dict[str, Any]] = []
    for pattern in patterns:
        strategy = "VCP Scanner" if pattern["name"] == "VCP" else "Rocket Base Scanner"
        reasons = [
            f"{pattern['name']} structure detected",
            f"Breakout level near {pattern['breakout_level']}",
            "Price is compressing after a controlled move",
        ]
        extra_signals.append(
            _build_signal(
                symbol=symbol,
                market=market,
                strategy=strategy,
                signal_type="bullish",
                score=max(7.0, pattern["strength"]),
                reasons=reasons,
                timeframe=timeframe,
                current_price=current_price,
                atr=atr,
                timestamp=timestamp,
                patterns=patterns,
            )
        )
    return extra_signals


def analyze_stock(symbol: str, market: str, df: pd.DataFrame, timeframe: str) -> List[Dict[str, Any]]:
    if df.empty or len(df) < 200:
        return []

    df = add_indicators(df)
    if df.empty or len(df) < 30:
        return []

    signals: List[Dict[str, Any]] = []
    last = df.iloc[-1]
    latest_timestamp = df.index[-1]
    atr = last["ATR"] if "ATR" in df.columns and not pd.isna(last["ATR"]) else (last["High"] - last["Low"])
    current_price = float(last["Close"])
    patterns = detect_patterns(df)

    strategies = {
        "Trend Continuation": evaluate_trend_continuation,
        "Pullback Setup": evaluate_pullback,
        "Breakout Scanner": evaluate_breakout,
        "Reversal": evaluate_reversal,
    }

    confluence_score = 0.0
    confluence_reasons: List[str] = []
    confluence_signal_type = None
    active_categories = set()

    for strategy_name, strategy_func in strategies.items():
        is_triggered, result = strategy_func(df)
        if not is_triggered:
            continue

        score = result["score"]
        reasons = list(result["reasons"])
        if "Volume" in df.columns:
            avg_vol = df["Volume"].iloc[-20:].mean()
            if last["Volume"] > avg_vol:
                score = min(10.0, score + 1.0)
                reasons.append("Supported by above-average volume")

        signal_payload = _build_signal(
            symbol=symbol,
            market=market,
            strategy=strategy_name,
            signal_type=result["signal"],
            score=score,
            reasons=reasons,
            timeframe=timeframe,
            current_price=current_price,
            atr=float(atr),
            timestamp=latest_timestamp,
            patterns=patterns,
        )
        signals.append(signal_payload)

        confluence_score += score
        confluence_reasons.extend(reasons)
        active_categories.update(signal_payload["categories"])
        if not confluence_signal_type:
            confluence_signal_type = result["signal"]
        elif confluence_signal_type != result["signal"]:
            confluence_signal_type = "mixed"

    signals.extend(
        _add_pattern_scanners(
            signals,
            patterns,
            symbol,
            market,
            timeframe,
            current_price,
            float(atr),
            latest_timestamp,
        )
    )
    active_categories.update(category for signal in signals for category in signal["categories"])

    if len(signals) >= 2 and confluence_signal_type and confluence_signal_type != "mixed":
        unique_reasons = list(dict.fromkeys(confluence_reasons))
        all_patterns = patterns
        high_confluence = _build_signal(
            symbol=symbol,
            market=market,
            strategy="High Confluence",
            signal_type=confluence_signal_type,
            score=min(10.0, (confluence_score / max(len(signals), 1)) + 1.5),
            reasons=unique_reasons[:5],
            timeframe=timeframe,
            current_price=current_price,
            atr=float(atr),
            timestamp=latest_timestamp,
            patterns=all_patterns,
        )
        high_confluence["categories"] = sorted(active_categories)
        high_confluence["confluence_score"] = round(high_confluence["score"] + len(signals), 2)
        high_confluence["analysis_summary"] = _build_analysis_summary(
            confluence_signal_type,
            high_confluence["confluence_score"],
            high_confluence["categories"],
            all_patterns,
            unique_reasons[:5],
        )
        high_confluence["probability"] = high_confluence["analysis_summary"]["probability"]
        signals.append(high_confluence)

    sorted_signals = sorted(
        signals,
        key=lambda signal: (
            len(signal["patterns"]),
            len(signal["categories"]),
            signal.get("confluence_score") or signal["score"],
            signal["score"],
        ),
        reverse=True,
    )
    return sorted_signals[:TOP_SIGNAL_LIMIT]
