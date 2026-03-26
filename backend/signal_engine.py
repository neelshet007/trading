import pandas as pd
from typing import List, Dict, Any
from indicators import add_indicators
from strategies import (
    evaluate_trend_continuation,
    evaluate_pullback,
    evaluate_breakout,
    evaluate_reversal
)

def analyze_stock(symbol: str, market: str, df: pd.DataFrame, timeframe: str) -> List[Dict[str, Any]]:
    if df.empty or len(df) < 200:
        return []

    # Apply indicators
    df = add_indicators(df)
    if df.empty:
        return []

    signals = []
    last = df.iloc[-1]
    
    # Calculate Risk-Reward Params broadly
    atr = last['ATR'] if 'ATR' in df.columns and not pd.isna(last['ATR']) else (last['High'] - last['Low'])
    current_price = last['Close']

    strategies = {
        "Trend Continuation": evaluate_trend_continuation,
        "Pullback Setup": evaluate_pullback,
        "Breakout Scanner": evaluate_breakout,
        "Reversal": evaluate_reversal
    }

    # High Confluence tracking
    confluence_score = 0
    confluence_reasons = []
    confluence_signal_type = None

    for st_name, strategy_func in strategies.items():
        is_triggered, result = strategy_func(df)
        if is_triggered:
            signal_type = result["signal"]
            # Estimate SL and Target based on ATR (1:2 Risk Reward)
            if signal_type == "bullish":
                stop_loss = current_price - (1.5 * atr)
                target = current_price + (3.0 * atr)
            else:
                stop_loss = current_price + (1.5 * atr)
                target = current_price - (3.0 * atr)

            score = result["score"]
            # Enhance score based on volume confirmation if any
            if 'Volume' in df.columns:
                avg_vol = df['Volume'].iloc[-20:].mean()
                if last['Volume'] > avg_vol:
                    score = min(10.0, score + 1.0)
                    result["reasons"].append("Supported by above-average volume")

            signals.append({
                "symbol": symbol,
                "market": market,
                "strategy": st_name,
                "signal": signal_type,
                "score": score,
                "reasons": result["reasons"],
                "timeframe": timeframe,
                "entry_zone": round(current_price, 2),
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "risk_reward": 2.0
            })

            # Confluence Logic
            confluence_score += score
            confluence_reasons.extend(result["reasons"])
            if not confluence_signal_type:
                confluence_signal_type = signal_type
            elif confluence_signal_type != signal_type:
                confluence_signal_type = "mixed"

    # High Confluence Strategy
    if len(signals) >= 2 and confluence_signal_type and confluence_signal_type != "mixed":
        avg_score = min(10.0, (confluence_score / len(signals)) + 1.5)
        # deduplicate reasons
        unique_reasons = list(set(confluence_reasons))
        signals.append({
            "symbol": symbol,
            "market": market,
            "strategy": "High Confluence",
            "signal": confluence_signal_type,
            "score": round(avg_score, 1),
            "reasons": unique_reasons[:5], # Keep top 5 reasons
            "timeframe": timeframe,
            "entry_zone": round(current_price, 2),
            "stop_loss": round(current_price - (1.5 * atr) if confluence_signal_type == 'bullish' else current_price + (1.5 * atr), 2),
            "target": round(current_price + (3.0 * atr) if confluence_signal_type == 'bullish' else current_price - (3.0 * atr), 2),
            "risk_reward": 2.0
        })

    return signals
