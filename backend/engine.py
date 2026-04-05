from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pandas as pd
import yfinance as yf

from schemas import ChecklistDetails, ConfluenceScore, DerivativeStats, ForensicReport, NarrativeDetail, SetupResponse
from trading_engine import build_signal_snapshot, evaluate_latest_signal, normalize_ohlcv


def _infer_market(symbol: str) -> str:
    upper = symbol.upper()
    if "-USD" in upper or upper.endswith("USD"):
        return "CRYPTO" if "-" in upper else "FOREX"
    if upper.endswith("=F"):
        return "COMMODITIES"
    return "STOCKS"


def _download_scan_data(symbol: str, interval: str = "1h", period: str = "18mo") -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    return normalize_ohlcv(df)


def _to_setup_response(symbol: str, signal, *, qualified: bool = True) -> SetupResponse:
    confluence = signal.score.as_dict() if hasattr(signal.score, "as_dict") else signal["score"].as_dict()
    signal_bias = signal.bias if hasattr(signal, "bias") else signal["bias"]
    signal_direction = signal.direction if hasattr(signal, "direction") else signal["direction"]
    entry = signal.entry if hasattr(signal, "entry") else signal["entry"]
    stop_loss = signal.stop_loss if hasattr(signal, "stop_loss") else signal["stop_loss"]
    take_profit = signal.take_profit if hasattr(signal, "take_profit") else signal["take_profit"]
    risk_reward = signal.risk_reward if hasattr(signal, "risk_reward") else signal["risk_reward"]
    liquidity_level = signal.liquidity_level if hasattr(signal, "liquidity_level") else signal["liquidity_level"]
    reasons = signal.reasons if hasattr(signal, "reasons") else signal["reasons"]
    confirmation_type = signal.confirmation_type if hasattr(signal, "confirmation_type") else signal["confirmation_type"]
    return SetupResponse(
        symbol=symbol,
        bias=signal_bias,
        status="Valid" if qualified else "Watching",
        entry=round(entry, 4),
        stop_loss=round(stop_loss, 4),
        take_profit=round(take_profit, 4),
        risk_reward=round(risk_reward, 2),
        confluence=ConfluenceScore(
            trend_alignment=confluence["trend_alignment"],
            fvg_mitigation=confluence["momentum"],
            idm_sweep=confluence["liquidity_sweep"],
            discount_premium=confluence["clean_pullback"],
            total_score=confluence["total"],
        ),
        narrative=NarrativeDetail(
            reason="Trend + Pullback + Liquidity Sweep + Confirmation" if qualified else "Market context mapped, waiting for full confirmation",
            location=f"Liquidity level near {round(liquidity_level, 4)}" if liquidity_level is not None else "Liquidity level not available",
            context="Deterministic high-probability setup with trend alignment, non-flat momentum, ATR expansion, pullback, and price-action confirmation." if qualified else "The engine found directional context, but one or more execution filters are still incomplete.",
            score_breakdown=[
                f"Trend alignment: +{confluence['trend_alignment']}",
                f"Momentum: +{confluence['momentum']}",
                f"Liquidity sweep: +{confluence['liquidity_sweep']}",
                f"Confirmation: +{confluence['confirmation']}",
                f"Clean pullback: +{confluence['clean_pullback']}",
            ],
            timeline=reasons,
            zoom_reason=f"Confirmation candle: {(confirmation_type or 'none').replace('_', ' ')}",
        ),
        ob_top=round(liquidity_level, 4) if signal_direction == "short" and liquidity_level is not None else None,
        ob_bottom=round(liquidity_level, 4) if signal_direction == "long" and liquidity_level is not None else None,
        zoom_resolution=signal.timeframe if hasattr(signal, "timeframe") else signal["timeframe"],
        trade_classification="SWING" if qualified else "WAIT",
        margin_multiple="1x",
        auto_square_off=None,
    )


def _scan_symbol(symbol: str) -> Optional[SetupResponse]:
    market = _infer_market(symbol)
    df = _download_scan_data(symbol)
    if df.empty:
        return None
    signal = evaluate_latest_signal(symbol, market, df)
    if signal is not None:
        return _to_setup_response(symbol, signal, qualified=True)
    snapshot = build_signal_snapshot(symbol, market, df)
    if snapshot is None or snapshot["score"].total <= 0:
        return None
    return _to_setup_response(symbol, snapshot, qualified=False)


def run_scan(symbols: list[str]) -> list[SetupResponse]:
    if not symbols:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as executor:
        results = list(executor.map(_scan_symbol, symbols))
    valid = [result for result in results if result is not None]
    valid.sort(key=lambda item: item.confluence.total_score, reverse=True)
    return valid


def run_forensic_scan(symbol: str) -> Optional[ForensicReport]:
    market = _infer_market(symbol)
    df = _download_scan_data(symbol)
    if df.empty:
        return None
    signal = evaluate_latest_signal(symbol, market, df)
    snapshot = build_signal_snapshot(symbol, market, df)
    if signal is None and snapshot is None:
        return None
    active = signal if signal is not None else snapshot
    checks = snapshot["checks"] if snapshot is not None else {
        "trend_ok": True,
        "momentum_ok": True,
        "atr_ok": True,
        "pullback_ok": True,
        "sweep_ok": True,
        "confirmation_ok": True,
    }
    qualified = signal is not None

    return ForensicReport(
        formation="Trend filter and volatility filter aligned before pullback into the 20 MA." if checks["trend_ok"] and checks["atr_ok"] else "Directional bias exists, but volatility or structure alignment is still developing.",
        catalyst=(
            f"Liquidity sweep detected near {round(active.sweep_level, 4)} followed by {active.confirmation_type.replace('_', ' ')} confirmation."
            if getattr(active, "sweep_level", None) is not None and getattr(active, "confirmation_type", None)
            else "No completed sweep-confirmation sequence yet. Wait for a cleaner pullback or confirmation candle."
        ),
        checklist=ChecklistDetails(
            htf_aligned=checks["trend_ok"],
            liquidity_swept=checks["sweep_ok"],
            fvg_created=False,
            in_discount=(active.direction == "long") if hasattr(active, "direction") else (active["direction"] == "long"),
        ),
        derivative_stats=DerivativeStats(
            oi_interpretation="Ready for execution" if qualified else "Tracking only - confirmation pending",
            max_pain_proxy=round(active.entry, 4) if hasattr(active, "entry") else round(active["entry"], 4),
        ),
        instruction="Risk 1% of equity, place stop beyond the swept liquidity zone, and halt the session after three consecutive losses." if qualified else "Do not enter yet. Wait for the missing checks to turn positive before taking risk.",
        entry=round(active.entry, 4) if hasattr(active, "entry") else round(active["entry"], 4),
        stop_loss=round(active.stop_loss, 4) if hasattr(active, "stop_loss") else round(active["stop_loss"], 4),
        take_profit=round(active.take_profit, 4) if hasattr(active, "take_profit") else round(active["take_profit"], 4),
        risk_reward=round(active.risk_reward, 2) if hasattr(active, "risk_reward") else round(active["risk_reward"], 2),
        zoom_resolution=active.timeframe if hasattr(active, "timeframe") else active["timeframe"],
        trade_classification="SWING" if qualified else "WAIT",
        margin_multiple="1x",
        auto_square_off=None,
    )
