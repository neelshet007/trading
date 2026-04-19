from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from indicators import add_indicators
from market_utils import ensure_utc, utc_now
from schemas import (
    ChecklistDetails,
    ConfluenceScore,
    DerivativeStats,
    ForensicReport,
    HumanLoopAssessment,
    MarketFootprint,
    NarrativeDetail,
    RegimeContext,
    RiskEnvelope,
    SetupResponse,
    TriggerPlan,
)

logger = logging.getLogger(__name__)
YF_CACHE_DIR = Path(__file__).resolve().parent / ".yf_cache"
YF_CACHE_DIR.mkdir(exist_ok=True)
if hasattr(yf, "set_tz_cache_location"):
    yf.set_tz_cache_location(str(YF_CACHE_DIR))

CORE_SYMBOLS = {"BTC-USD", "ETH-USD", "SOL-USD"}
BIG_THREE_ORDER = {"BTC-USD": 0, "ETH-USD": 1, "SOL-USD": 2}
ETF_CORRELATION_FACTORS = ["DXY proxy softens risk appetite", "Spot ETF flow tone matters for BTC and ETH"]


@dataclass
class TimeframeBundle:
    symbol: str
    daily: pd.DataFrame
    h4: pd.DataFrame
    h1: pd.DataFrame
    m15: pd.DataFrame
    m5: pd.DataFrame
    m1: pd.DataFrame


def _history(symbol: str, period: str, interval: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    frame = ticker.history(period=period, interval=interval, auto_adjust=False, actions=False, prepost=True)
    if isinstance(frame.index, pd.DatetimeIndex):
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        else:
            frame.index = frame.index.tz_convert("UTC")
    return frame.dropna(how="all")


def fetch_symbol_bundle(symbol: str) -> Optional[TimeframeBundle]:
    try:
        bundle = TimeframeBundle(
            symbol=symbol,
            daily=_history(symbol, "180d", "1d"),
            h4=_history(symbol, "90d", "1h").resample("4h").agg(
                {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
            ).dropna(),
            h1=_history(symbol, "60d", "1h"),
            m15=_history(symbol, "10d", "15m"),
            m5=_history(symbol, "5d", "5m"),
            m1=_history(symbol, "2d", "1m"),
        )
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", symbol, exc)
        return None

    if bundle.daily.empty or bundle.h4.empty or bundle.h1.empty or bundle.m15.empty or bundle.m5.empty:
        return None
    return bundle


def _atr(df: pd.DataFrame, window: int = 14) -> float:
    enriched = add_indicators(df.tail(max(len(df), window + 20)).copy())
    if "ATR" in enriched.columns and not enriched.empty:
        value = enriched["ATR"].iloc[-1]
        if pd.notna(value):
            return float(value)
    latest = df.iloc[-1]
    return float(latest["High"] - latest["Low"])


def _returns(series: pd.Series) -> pd.Series:
    return np.log(series / series.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()


def infer_three_state_hmm(h1: pd.DataFrame) -> tuple[int, str, float]:
    returns = _returns(h1["Close"])
    if len(returns) < 50:
        return 2, "Regime 2 - Directional Expansion", 0.5

    vol = returns.rolling(24).std().dropna()
    trend = returns.rolling(24).mean().abs().dropna()
    shared = pd.concat([vol.rename("vol"), trend.rename("trend")], axis=1).dropna()
    if shared.empty:
        return 2, "Regime 2 - Directional Expansion", 0.5

    latest = shared.iloc[-1]
    vol_low, vol_high = shared["vol"].quantile([0.33, 0.66])
    trend_low, trend_high = shared["trend"].quantile([0.33, 0.66])

    if latest["vol"] <= vol_low and latest["trend"] <= trend_low:
        confidence = 1.0 - ((latest["vol"] / max(vol_low, 1e-9)) * 0.5)
        return 1, "Regime 1 - Low Volatility Consolidation", round(float(min(max(confidence, 0.5), 0.95)), 2)
    if latest["vol"] >= vol_high and latest["trend"] >= trend_high:
        confidence = min(0.95, 0.55 + ((latest["vol"] - vol_high) / max(vol_high, 1e-9)))
        return 2, "Regime 2 - Directional Expansion", round(float(max(confidence, 0.55)), 2)
    confidence = min(0.92, 0.52 + ((latest["vol"] - vol_low) / max(vol_high - vol_low, 1e-9)) * 0.25)
    return 3, "Regime 3 - High Volatility Repricing", round(float(max(confidence, 0.52)), 2)


def _ipda_cycle(daily: pd.DataFrame) -> tuple[str, float, float]:
    last_close = float(daily["Close"].iloc[-1])
    ranges = {}
    for lookback in (20, 40, 60):
        window = daily.tail(lookback)
        ranges[lookback] = (float(window["Low"].min()), float(window["High"].max()))
    low_60, high_60 = ranges[60]
    percentile = 0.5 if math.isclose(high_60, low_60) else (last_close - low_60) / (high_60 - low_60)
    if percentile < 0.3:
        state = "20-40-60 day discount delivery"
    elif percentile > 0.7:
        state = "20-40-60 day premium delivery"
    else:
        state = "20-40-60 day rebalancing"
    return state, low_60, high_60


def _institutional_bias(daily: pd.DataFrame, h4: pd.DataFrame) -> str:
    daily_ma = float(daily["Close"].rolling(20).mean().iloc[-1])
    h4_ma = float(h4["Close"].rolling(20).mean().iloc[-1])
    close_daily = float(daily["Close"].iloc[-1])
    close_h4 = float(h4["Close"].iloc[-1])
    if close_daily > daily_ma and close_h4 > h4_ma:
        return "bullish"
    if close_daily < daily_ma and close_h4 < h4_ma:
        return "bearish"
    return "neutral"


def _find_recent_fvg(df: pd.DataFrame, bias: str) -> tuple[Optional[float], Optional[float], str]:
    scan = df.tail(80).copy()
    if len(scan) < 5:
        return None, None, "No recent FVG"

    if bias == "bullish":
        mask = (scan["High"].shift(2) < scan["Low"]) & (scan["Close"].shift(1) > scan["High"].shift(2))
        if mask.any():
            idx = scan[mask].index[-1]
            return float(scan["High"].shift(2).loc[idx]), float(scan["Low"].loc[idx]), "Bullish BOS"
    else:
        mask = (scan["Low"].shift(2) > scan["High"]) & (scan["Close"].shift(1) < scan["Low"].shift(2))
        if mask.any():
            idx = scan[mask].index[-1]
            return float(scan["High"].loc[idx]), float(scan["Low"].shift(2).loc[idx]), "Bearish CHoCH"
    return None, None, "No recent FVG"


def _find_order_block(df: pd.DataFrame, bias: str) -> tuple[Optional[float], Optional[float]]:
    recent = df.tail(50)
    if bias == "bullish":
        candidates = recent[recent["Close"] < recent["Open"]]
    else:
        candidates = recent[recent["Close"] > recent["Open"]]
    if candidates.empty:
        return None, None
    candle = candidates.iloc[-1]
    return float(candle["Low"]), float(candle["High"])


def _detect_choch_and_displacement(df: pd.DataFrame, bias: str) -> tuple[str, float]:
    sample = df.tail(30).copy()
    if len(sample) < 10:
        return "No clear CHoCH", 0.0
    recent_high = float(sample["High"].iloc[-10:-1].max())
    recent_low = float(sample["Low"].iloc[-10:-1].min())
    close = float(sample["Close"].iloc[-1])
    atr_proxy = float((sample["High"] - sample["Low"]).tail(10).mean())
    displacement = abs(close - float(sample["Open"].iloc[-1])) / max(atr_proxy, 1e-9)
    if bias == "bullish" and close > recent_high:
        return "Bullish CHoCH with displacement", round(displacement, 2)
    if bias == "bearish" and close < recent_low:
        return "Bearish CHoCH with displacement", round(displacement, 2)
    return "CHoCH pending", round(displacement, 2)


def _fib_ote(h1: pd.DataFrame, bias: str) -> tuple[float, str]:
    window = h1.tail(72)
    high = float(window["High"].max())
    low = float(window["Low"].min())
    close = float(window["Close"].iloc[-1])
    if bias == "bullish":
        ote = high - ((high - low) * 0.705)
        state = "discount" if close <= (high + low) / 2 else "premium"
    else:
        ote = low + ((high - low) * 0.705)
        state = "premium" if close >= (high + low) / 2 else "discount"
    return float(ote), state


def _cvd_divergence(m5: pd.DataFrame, bias: str) -> str:
    sample = m5.tail(48).copy()
    if sample.empty:
        return "Unavailable"
    delta = np.where(sample["Close"] >= sample["Open"], sample["Volume"], -sample["Volume"])
    sample["cvd"] = np.cumsum(delta)
    price_now = float(sample["Close"].iloc[-1])
    price_ref = float(sample["Close"].iloc[-12])
    cvd_now = float(sample["cvd"].iloc[-1])
    cvd_ref = float(sample["cvd"].iloc[-12])
    if bias == "bullish" and price_now <= price_ref and cvd_now > cvd_ref:
        return "Bullish divergence"
    if bias == "bearish" and price_now >= price_ref and cvd_now < cvd_ref:
        return "Bearish divergence"
    return "Neutral"


def _liquidity_sweep(m5: pd.DataFrame, bias: str) -> bool:
    sample = m5.tail(24)
    if len(sample) < 6:
        return False
    last = sample.iloc[-1]
    prior = sample.iloc[:-1]
    if bias == "bullish":
        return bool(last["Low"] < prior["Low"].tail(8).min() and last["Close"] > prior["Low"].tail(8).min())
    return bool(last["High"] > prior["High"].tail(8).max() and last["Close"] < prior["High"].tail(8).max())


def _magnetic_liquidity_zones(m5: pd.DataFrame, bias: str) -> list[str]:
    sample = m5.tail(40)
    if sample.empty:
        return []
    zones: list[str] = []
    equal_highs = sample["High"].round(4).value_counts()
    equal_lows = sample["Low"].round(4).value_counts()
    if not equal_highs[equal_highs >= 2].empty:
        zones.append(f"Stops clustered near highs {equal_highs[equal_highs >= 2].index[0]}")
    if not equal_lows[equal_lows >= 2].empty:
        zones.append(f"Stops clustered near lows {equal_lows[equal_lows >= 2].index[0]}")
    if not zones:
        latest = float(sample["High"].tail(5).max() if bias == "bearish" else sample["Low"].tail(5).min())
        zones.append(f"Nearest liquidity pool around {latest:.4f}")
    return zones[:2]


def _silver_bullet_window(timestamp: pd.Timestamp) -> bool:
    hour = ensure_utc(timestamp.to_pydatetime()).hour
    return hour in {8, 9, 14, 15}


def _entry_model(m1: pd.DataFrame, m5: pd.DataFrame, bias: str, ote: float) -> tuple[str, str]:
    sweep = _liquidity_sweep(m5, bias)
    fvg_low, fvg_high, _ = _find_recent_fvg(m1 if len(m1) > 10 else m5, bias)
    in_session = _silver_bullet_window(m5.index[-1])
    if sweep and fvg_low is not None and fvg_high is not None:
        return "Unicorn Model (Breaker + FVG)", "Breaker reclaim plus fresh imbalance on LTF."
    if sweep and in_session:
        return "Silver Bullet Session Sweep", "Session sweep completed inside a defined liquidity window."
    if abs(float(m5["Close"].iloc[-1]) - ote) / max(ote, 1e-9) < 0.005:
        return "OTE Retracement Tap", "Price is trading directly into the 0.705 retracement."
    return "Turtle Soup", "Counterparty liquidity sweep with re-entry trigger."


def _gjr_garch_volatility(h1: pd.DataFrame) -> float:
    returns = _returns(h1["Close"])
    if len(returns) < 20:
        return 0.02
    omega = max(returns.var() * 0.02, 1e-8)
    alpha = 0.08
    gamma = 0.12
    beta = 0.82
    variance = returns.var()
    for ret in returns.tail(120):
        shock = float(ret)
        variance = omega + alpha * (shock ** 2) + gamma * ((shock < 0) * (shock ** 2)) + beta * variance
    return float(math.sqrt(max(variance, 1e-9)))


def _risk_envelope(symbol: str, entry: float, stop_loss: float, h1: pd.DataFrame, confluence_total: int) -> RiskEnvelope:
    gjr_vol = _gjr_garch_volatility(h1)
    var_95 = round(entry * gjr_vol * 1.65, 4)
    stop_distance = abs(entry - stop_loss)
    r_multiple = round((stop_distance * 2.5) / max(stop_distance, 1e-9), 2)
    win_rate = min(0.72, max(0.38, 0.42 + (confluence_total / 20)))
    expectancy = round((win_rate * r_multiple) - (1 - win_rate), 2)
    base_slippage = 4.8 if symbol == "BTC-USD" else 6.8 if symbol == "ETH-USD" else 8.8
    size_cap = 0.15 if symbol == "ETH-USD" else 0.12 if symbol in CORE_SYMBOLS else 0.08
    recommended = max(0.02, min(size_cap, 0.02 + (confluence_total / 100)))
    slippage = round(min(18.5, base_slippage + (gjr_vol * 1000 * 0.35) + (recommended / size_cap) * 1.2), 2)
    funding_clamp = round(min(18.0, 4.0 + gjr_vol * 220), 2)
    convexity_risk = round((gjr_vol * math.sqrt(24)) * (1 + slippage / 10), 4)
    fee_bps = 10.0
    total_friction = round(fee_bps + slippage, 2)
    return RiskEnvelope(
        var_95=var_95,
        gjr_garch_vol=round(gjr_vol, 4),
        convexity_risk=convexity_risk,
        expected_slippage_bps=slippage,
        funding_rate_clamp_bps=funding_clamp,
        max_equity_allocation=size_cap,
        recommended_equity_allocation=round(recommended, 4),
        r_multiple=r_multiple,
        expectancy=expectancy,
        fee_bps=fee_bps,
        total_friction_bps=total_friction,
    )


def _build_hitl(symbol: str, regime_label: str, footprint: MarketFootprint, trigger: TriggerPlan) -> HumanLoopAssessment:
    traps = [
        "Watch for inducement just above obvious intraday equal highs before continuation.",
        "Do not trust the first reclaim if CVD diverges back against the entry candle.",
        "If the FVG is tiny versus ATR, the move may just be mean reversion noise.",
    ]
    if symbol == "ETH-USD":
        traps.append("ETH size should stay below the 15% equity cap because slippage expands quickly above 7.76 bps.")
    if regime_label.startswith("Regime 3"):
        traps.append("High-volatility repricing can overshoot clean SMC levels before stabilizing.")
    checks = [
        "Confirm the sweep actually ran resting stops rather than printing a shallow inside-bar wick.",
        "Verify the OTE tap occurs at or below 0.705 for longs, or at or above 0.705 for shorts.",
        f"Invalidate the setup if price accepts beyond {trigger.stop_loss:.2f} on the execution timeframe.",
    ]
    return HumanLoopAssessment(
        inducement_traps=traps,
        human_checks=checks,
        automation_risk="Medium. Structure is machine-detectable, but inducement quality and sweep intent still need human judgment.",
    )


def _probability_score(
    *,
    symbol: str,
    bias: str,
    regime_state: int,
    confluence_total: int,
    premium_discount: str,
    sweep_confirmed: bool,
    cvd: str,
    displacement: float,
    btc_headwind: bool,
) -> int:
    score = 18 + (confluence_total * 7)
    if bias == "bullish":
        score += 8
    if regime_state == 2:
        score += 12
    elif regime_state == 3:
        score += 4
    else:
        score -= 18
    if premium_discount == "discount" and bias == "bullish":
        score += 10
    if premium_discount == "premium" and bias == "bearish":
        score += 10
    if sweep_confirmed:
        score += 8
    if "divergence" in cvd.lower():
        score += 6
    score += min(8, int(displacement * 2))
    if btc_headwind and symbol not in CORE_SYMBOLS:
        score -= 12
    return max(5, min(95, int(score)))


def _verdict(probability_score: int, bias: str) -> str:
    if bias == "bullish" and probability_score >= 75:
        return "STRONG BUY"
    if probability_score >= 55:
        return "NEUTRAL"
    return "AVOID"


def _primary_failure(
    *,
    bias: str,
    regime_state: int,
    premium_discount: str,
    sweep_confirmed: bool,
    cvd: str,
    fvg_low: Optional[float],
    btc_headwind: bool,
) -> str:
    if regime_state == 1:
        return "Regime 1 consolidation is suppressing directional follow-through."
    if bias == "bullish" and premium_discount != "discount":
        return "Price is not in discount and has not reached the 0.705 OTE long entry zone."
    if bias == "bullish" and not sweep_confirmed:
        return "No confirmed liquidation sweep of retail stops, so the long trigger is incomplete."
    if "divergence" not in cvd.lower():
        return "CVD is not confirming the move, which raises exhaustion risk."
    if fvg_low is None:
        return "No actionable imbalance is open on the medium timeframe."
    if btc_headwind and bias == "bullish":
        return "BTC beta is bearish-to-stalled, which is suppressing altcoin probability."
    return "Structure is informative, but the execution stack is not fully aligned."


def _beta_headwind(reference_setup: Optional[SetupResponse]) -> bool:
    if reference_setup is None:
        return False
    return reference_setup.context.hmm_state == 1 or reference_setup.bias == "bearish" or reference_setup.verdict == "AVOID"


def _sort_key(item: SetupResponse) -> tuple[int, int, int, float]:
    if item.symbol in BIG_THREE_ORDER:
        return (0, BIG_THREE_ORDER[item.symbol], -item.probability_score, -item.risk.expectancy)
    return (1, 99, -item.probability_score, -item.risk.expectancy)


def build_setup(bundle: TimeframeBundle) -> Optional[SetupResponse]:
    symbol = bundle.symbol
    regime_state, regime_label, confidence = infer_three_state_hmm(bundle.h1)
    ipda_cycle, range_low, range_high = _ipda_cycle(bundle.daily)
    bias = _institutional_bias(bundle.daily, bundle.h4)
    if bias == "neutral":
        bias = "bearish" if float(bundle.h4["Close"].iloc[-1]) < float(bundle.h4["Close"].iloc[-8]) else "bullish"

    ote, premium_discount = _fib_ote(bundle.h1, bias)
    fvg_low, fvg_high, structure_signal = _find_recent_fvg(bundle.m15, bias)
    ob_low, ob_high = _find_order_block(bundle.h4, bias)
    sweep_confirmed = _liquidity_sweep(bundle.m5, bias)
    cvd = _cvd_divergence(bundle.m5, bias)
    choch_label, displacement = _detect_choch_and_displacement(bundle.m5, bias)
    liquidity_zones = _magnetic_liquidity_zones(bundle.m5, bias)
    atr = _atr(bundle.m15)
    current_price = float(bundle.m5["Close"].iloc[-1])
    if bias == "bullish":
        entry_price = min(current_price, ote)
        stop_loss = (ob_low if ob_low is not None else entry_price - (atr * 1.2))
        take_profit = entry_price + max(entry_price - stop_loss, atr) * 2.5
    else:
        entry_price = max(current_price, ote)
        stop_loss = (ob_high if ob_high is not None else entry_price + (atr * 1.2))
        take_profit = entry_price - max(stop_loss - entry_price, atr) * 2.5

    status = "qualified"
    if regime_state == 1:
        status = "regime-blocked"
    elif bias == "bullish" and not sweep_confirmed:
        status = "await-sweep"
    elif bias == "bullish" and premium_discount != "discount":
        status = "premium-not-buy-zone"
    elif bias == "bearish" and premium_discount != "premium":
        status = "discount-not-short-zone"
    elif fvg_low is None or fvg_high is None:
        status = "imbalance-missing"

    entry_model, confirmation = _entry_model(bundle.m1, bundle.m5, bias, ote)
    footprint = MarketFootprint(
        htf_range_low=round(range_low, 4),
        htf_range_high=round(range_high, 4),
        nearest_order_block_low=round(ob_low, 4) if ob_low is not None else None,
        nearest_order_block_high=round(ob_high, 4) if ob_high is not None else None,
        nearest_fvg_low=round(fvg_low, 4),
        nearest_fvg_high=round(fvg_high, 4),
        fvg_atr_multiple=round(abs(fvg_high - fvg_low) / max(atr, 1e-9), 2),
        premium_discount_state=premium_discount,
        ote_level=round(ote, 4),
        structure_signal=f"{structure_signal} | {choch_label}",
        cvd_divergence=cvd,
        liquidation_sweep_confirmed=sweep_confirmed,
        magnetic_liquidity_zones=liquidity_zones,
    )
    confluence = ConfluenceScore(
        trend_alignment=2,
        fvg_mitigation=0 if fvg_low is None else 2 if footprint.fvg_atr_multiple and footprint.fvg_atr_multiple < 1.1 else 3,
        idm_sweep=3 if sweep_confirmed else 0,
        discount_premium=3 if premium_discount == "discount" and bias == "bullish" or premium_discount == "premium" and bias == "bearish" else 0,
        order_flow_alignment=2 if "divergence" in cvd.lower() else 1,
    )
    confluence.total_score = min(
        10,
        confluence.trend_alignment
        + confluence.fvg_mitigation
        + confluence.idm_sweep
        + confluence.discount_premium
        + confluence.order_flow_alignment,
    )
    risk = _risk_envelope(symbol, entry_price, stop_loss, bundle.h1, confluence.total_score)
    trigger = TriggerPlan(
        entry_model=entry_model,
        entry_price=round(entry_price, 4),
        entry_band_low=round(min(entry_price, fvg_low, fvg_high), 4),
        entry_band_high=round(max(entry_price, fvg_low, fvg_high), 4),
        stop_loss=round(stop_loss, 4),
        take_profit=round(take_profit, 4),
        invalidation="Abort if price closes through the OB boundary and fails to reclaim the swept liquidity pool.",
        execution_timeframe="5M / 1M",
        confirmation=confirmation,
    )
    context = RegimeContext(
        hmm_state=regime_state,
        hmm_regime=regime_label,
        regime_confidence=confidence,
        ipda_cycle=ipda_cycle,
        institutional_bias=bias,
        correlated_factors=ETF_CORRELATION_FACTORS,
    )
    hitl = _build_hitl(symbol, regime_label, footprint, trigger)
    probability_score = _probability_score(
        symbol=symbol,
        bias=bias,
        regime_state=regime_state,
        confluence_total=confluence.total_score,
        premium_discount=premium_discount,
        sweep_confirmed=sweep_confirmed,
        cvd=cvd,
        displacement=displacement,
        btc_headwind=False,
    )
    verdict = _verdict(probability_score, bias)
    primary_failure = _primary_failure(
        bias=bias,
        regime_state=regime_state,
        premium_discount=premium_discount,
        sweep_confirmed=sweep_confirmed,
        cvd=cvd,
        fvg_low=fvg_low,
        btc_headwind=False,
    )
    why_buy = (
        f"Buy only if price trades back into discount and taps the 0.705 OTE near {ote:.4f}, "
        f"then confirms with {entry_model} and respects the nearest OB."
    )
    why_sell_wait = (
        primary_failure if verdict != "STRONG BUY"
        else f"Wait if price reclaims premium or fails to hold the OB/FVG stack despite the current long thesis."
    )
    forensic_evidence = [
        f"HTF OB sits between {ob_low:.4f} and {ob_high:.4f}." if ob_low is not None and ob_high is not None else "HTF order block is weak or already mitigated.",
        f"Open FVG spans {fvg_low:.4f} to {fvg_high:.4f} and measures {footprint.fvg_atr_multiple} ATR." if fvg_low is not None and fvg_high is not None else "No open medium-timeframe FVG is acting as a price magnet.",
        f"{choch_label}; displacement registered at {displacement} ATR on the lower timeframe.",
    ]
    narrative = NarrativeDetail(
        reason=f"{entry_model} aligned with {structure_signal} and {'a fresh liquidity sweep' if sweep_confirmed else 'an unconfirmed sweep path'}.",
        location=f"{ipda_cycle}; working inside the nearest {'discount' if bias == 'bullish' else 'premium'} dealing range.",
        context=f"{symbol} is trading with {regime_label.lower()} and {bias} HTF alignment. The setup only remains actionable while price respects the nearby order block.",
        score_breakdown=[
            f"HMM regime filter: state {regime_state}",
            f"IPDA cycle: {ipda_cycle}",
            f"FVG size: {footprint.fvg_atr_multiple} ATR",
            f"CVD: {cvd}",
            f"VaR95: {risk.var_95}",
        ],
        timeline=[
            f"HTF range defined between {range_low:.2f} and {range_high:.2f}.",
            f"Structure tagged {structure_signal} on the medium timeframe.",
            f"Execution model selected: {entry_model}.",
            "Human review required for inducement quality before order release.",
        ],
        zoom_reason="Execution shifts to 5M/1M because the sweep and imbalance already formed on the medium timeframe.",
    )
    return SetupResponse(
        symbol=symbol,
        bias=bias,
        status=status,
        probability_score=probability_score,
        verdict=verdict,
        primary_failure=primary_failure,
        market_beta_note=None,
        why_buy=why_buy,
        why_sell_wait=why_sell_wait,
        forensic_evidence=forensic_evidence,
        timestamp=ensure_utc(bundle.m5.index[-1].to_pydatetime()),
        entry=round(entry_price, 4),
        stop_loss=round(stop_loss, 4),
        take_profit=round(take_profit, 4),
        risk_reward=risk.r_multiple,
        confluence=confluence,
        context=context,
        footprint=footprint,
        trigger=trigger,
        risk=risk,
        hitl=hitl,
        narrative=narrative,
        ob_top=round(ob_high, 4) if ob_high is not None else None,
        ob_bottom=round(ob_low, 4) if ob_low is not None else None,
        zoom_resolution="5m / 1m",
        trade_classification="intraday swing continuation",
        margin_multiple="spot / perp with funding clamp",
        auto_square_off=None,
    )


def _scan_symbol(symbol: str) -> Optional[SetupResponse]:
    bundle = fetch_symbol_bundle(symbol)
    if bundle is None:
        return None
    try:
        return build_setup(bundle)
    except Exception as exc:
        logger.warning("Setup build failed for %s: %s", symbol, exc)
        return None


def run_scan(symbols: Iterable[str]) -> list[SetupResponse]:
    items = list(dict.fromkeys(symbols))
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(items))) as executor:
        results = [result for result in executor.map(_scan_symbol, items) if result is not None]
    btc_setup = next((item for item in results if item.symbol == "BTC-USD"), None)
    btc_headwind = _beta_headwind(btc_setup)
    for item in results:
        if btc_headwind and item.symbol not in CORE_SYMBOLS:
            item.market_beta_note = "BTC is not in a clean bullish expansion regime, which is suppressing altcoin probability."
            item.probability_score = max(5, item.probability_score - 12)
            item.primary_failure = item.primary_failure or "BTC beta headwind is suppressing alt follow-through."
            item.why_sell_wait = item.primary_failure
            item.verdict = _verdict(item.probability_score, item.bias)
        elif item.symbol == "BTC-USD":
            item.market_beta_note = "BTC sets market beta for the rest of the crypto watch-list."
        else:
            item.market_beta_note = "BTC beta is supportive enough that this asset can trade on its own structure."
    return sorted(results, key=_sort_key)


def run_forensic_scan(symbol: str) -> Optional[ForensicReport]:
    bundle = fetch_symbol_bundle(symbol)
    if bundle is None:
        return None
    setup = build_setup(bundle)
    if setup is None:
        return None
    return ForensicReport(
        symbol=setup.symbol,
        formation=setup.narrative.location if setup.narrative else "Crypto structure aligned.",
        catalyst=setup.narrative.reason if setup.narrative else setup.trigger.entry_model,
        checklist=ChecklistDetails(
            regime_allows_execution=setup.context.hmm_state != 1,
            liquidity_swept=setup.footprint.liquidation_sweep_confirmed,
            fvg_created=setup.footprint.nearest_fvg_low is not None,
            in_ote_zone=bool(setup.footprint.ote_level and abs(setup.entry - setup.footprint.ote_level) / max(setup.entry, 1e-9) <= 0.01),
            cvd_supportive="divergence" in setup.footprint.cvd_divergence.lower(),
        ),
        derivative_stats=DerivativeStats(
            funding_rate_clamp_bps=setup.risk.funding_rate_clamp_bps,
            liquidation_bias="Long-side stops swept" if setup.bias == "bullish" else "Short-side stops swept",
            cvd_divergence=setup.footprint.cvd_divergence,
        ),
        instruction=f"Execute only after human confirmation of the sweep quality. Use {setup.trigger.execution_timeframe} confirmation and invalidate below/above {setup.stop_loss:.4f}.",
        entry=setup.entry or 0.0,
        stop_loss=setup.stop_loss or 0.0,
        take_profit=setup.take_profit or 0.0,
        risk_reward=setup.risk.r_multiple,
        context=setup.context,
        footprint=setup.footprint,
        risk=setup.risk,
        hitl=setup.hitl,
        zoom_resolution=setup.zoom_resolution,
        trade_classification=setup.trade_classification,
        margin_multiple=setup.margin_multiple,
        auto_square_off=setup.auto_square_off,
    )
