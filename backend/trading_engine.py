from __future__ import annotations

from collections import deque
from dataclasses import asdict
from math import sqrt
from typing import Any, Optional

import numpy as np
import pandas as pd

from trading_config import load_market_config
from trading_types import BacktestTrade, MarketConfig, StrategyScore, TradeSignal


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    frame = df.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        flattened_columns: list[str] = []
        for column in frame.columns:
            if isinstance(column, tuple):
                flattened_columns.append(next((str(part) for part in column if part and part != ""), str(column[0])))
            else:
                flattened_columns.append(str(column))
        frame.columns = flattened_columns
    else:
        frame.columns = [str(col) for col in frame.columns]

    required = ["Open", "High", "Low", "Close", "Volume"]

    normalized = pd.DataFrame(index=frame.index)
    for column in required:
        matches = [existing for existing in frame.columns if existing == column]
        if matches:
            selected = frame.loc[:, matches]
            if isinstance(selected, pd.DataFrame):
                normalized[column] = pd.to_numeric(selected.iloc[:, 0], errors="coerce")
            else:
                normalized[column] = pd.to_numeric(selected, errors="coerce")
        else:
            normalized[column] = 0.0

    frame = normalized
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    if isinstance(frame.index, pd.DatetimeIndex):
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        else:
            frame.index = frame.index.tz_convert("UTC")
    return frame


def compute_features(df: pd.DataFrame, config: MarketConfig) -> pd.DataFrame:
    frame = normalize_ohlcv(df)
    if frame.empty:
        return frame

    frame["trend_ma"] = frame["Close"].rolling(config.trend_ma_period).mean()
    frame["signal_ma"] = frame["Close"].rolling(config.signal_ma_period).mean()

    prev_close = frame["Close"].shift(1)
    tr_components = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - prev_close).abs(),
            (frame["Low"] - prev_close).abs(),
        ],
        axis=1,
    )
    frame["true_range"] = tr_components.max(axis=1)
    frame["atr"] = frame["true_range"].rolling(config.atr_period).mean()
    frame["atr_pct"] = np.where(frame["Close"] != 0, frame["atr"] / frame["Close"], np.nan)

    shifted_ma = frame["signal_ma"].shift(config.momentum_lookback)
    frame["ma_slope_pct"] = np.where(
        shifted_ma.notna() & (shifted_ma != 0),
        ((frame["signal_ma"] - shifted_ma) / shifted_ma) * 100.0,
        np.nan,
    )

    body = (frame["Close"] - frame["Open"]).abs()
    upper_wick = frame["High"] - frame[["Open", "Close"]].max(axis=1)
    lower_wick = frame[["Open", "Close"]].min(axis=1) - frame["Low"]
    range_size = frame["High"] - frame["Low"]
    frame["body"] = body
    frame["upper_wick"] = upper_wick.clip(lower=0)
    frame["lower_wick"] = lower_wick.clip(lower=0)
    frame["range_size"] = range_size.replace(0, np.nan)

    return frame


def _market_to_config_name(market: str) -> str:
    normalized = market.upper()
    if normalized in {"USA", "INDIA", "STOCK", "STOCKS", "EQUITY", "EQUITIES"}:
        return "stocks"
    if normalized in {"CRYPTO"}:
        return "crypto"
    if normalized in {"FOREX", "FX"}:
        return "forex"
    if normalized in {"COMMODITIES", "COMMODITY"}:
        return "commodities"
    return normalized.lower()


def resolve_market_config(market: str) -> MarketConfig:
    return load_market_config(_market_to_config_name(market))


def _is_swing_high(frame: pd.DataFrame, idx: int, window: int) -> bool:
    if idx < window or idx + window >= len(frame):
        return False
    high = frame["High"].iloc[idx]
    left = frame["High"].iloc[idx - window:idx]
    right = frame["High"].iloc[idx + 1:idx + 1 + window]
    return bool((high > left.max()) and (high >= right.max()))


def _is_swing_low(frame: pd.DataFrame, idx: int, window: int) -> bool:
    if idx < window or idx + window >= len(frame):
        return False
    low = frame["Low"].iloc[idx]
    left = frame["Low"].iloc[idx - window:idx]
    right = frame["Low"].iloc[idx + 1:idx + 1 + window]
    return bool((low < left.min()) and (low <= right.min()))


def _find_latest_liquidity_levels(frame: pd.DataFrame, end_idx: int, config: MarketConfig) -> dict[str, Optional[dict[str, Any]]]:
    recent_high: Optional[dict[str, Any]] = None
    recent_low: Optional[dict[str, Any]] = None
    equal_high: Optional[dict[str, Any]] = None
    equal_low: Optional[dict[str, Any]] = None
    tolerance = float(frame["atr"].iloc[end_idx]) * config.equal_level_tolerance_atr if pd.notna(frame["atr"].iloc[end_idx]) else 0.0
    previous_swing_high: Optional[dict[str, Any]] = None
    previous_swing_low: Optional[dict[str, Any]] = None

    for idx in range(config.swing_window, end_idx - config.swing_window + 1):
        if _is_swing_high(frame, idx, config.swing_window):
            recent_high = {"index": idx, "price": float(frame["High"].iloc[idx]), "timestamp": frame.index[idx]}
            if previous_swing_high and abs(recent_high["price"] - previous_swing_high["price"]) <= tolerance:
                equal_high = recent_high
            previous_swing_high = recent_high
        if _is_swing_low(frame, idx, config.swing_window):
            recent_low = {"index": idx, "price": float(frame["Low"].iloc[idx]), "timestamp": frame.index[idx]}
            if previous_swing_low and abs(recent_low["price"] - previous_swing_low["price"]) <= tolerance:
                equal_low = recent_low
            previous_swing_low = recent_low

    return {
        "swing_high": recent_high,
        "swing_low": recent_low,
        "equal_high": equal_high,
        "equal_low": equal_low,
    }


def _trend_bias(row: pd.Series) -> str:
    if pd.isna(row["trend_ma"]):
        return "neutral"
    if row["Close"] > row["trend_ma"]:
        return "bullish"
    if row["Close"] < row["trend_ma"]:
        return "bearish"
    return "neutral"


def _momentum_ok(row: pd.Series, direction: str, config: MarketConfig) -> bool:
    slope = row["ma_slope_pct"]
    if pd.isna(slope):
        return False
    if direction == "long":
        return slope >= config.min_slope_pct
    return slope <= -config.min_slope_pct


def _atr_ok(row: pd.Series, config: MarketConfig) -> bool:
    atr_pct = row["atr_pct"]
    return bool(pd.notna(atr_pct) and atr_pct >= config.atr_threshold_pct)


def _pullback_ok(row: pd.Series, direction: str, config: MarketConfig) -> tuple[bool, float]:
    if pd.isna(row["signal_ma"]) or pd.isna(row["atr"]) or row["atr"] <= 0:
        return False, np.nan
    distance_atr = abs(row["Close"] - row["signal_ma"]) / row["atr"]
    inside_band = config.pullback_min_distance_atr <= distance_atr <= config.pullback_max_distance_atr
    touch_ma = (
        row["Low"] <= row["signal_ma"] <= row["Close"]
        if direction == "long"
        else row["High"] >= row["signal_ma"] >= row["Close"]
    )
    return bool(inside_band and touch_ma), float(distance_atr)


def _confirmation_type(frame: pd.DataFrame, idx: int, direction: str, config: MarketConfig) -> Optional[str]:
    if idx < 1:
        return None

    row = frame.iloc[idx]
    prev = frame.iloc[idx - 1]
    atr = row["atr"]
    body = row["body"]

    if direction == "long":
        bullish_engulfing = (
            row["Close"] > row["Open"]
            and prev["Close"] < prev["Open"]
            and row["Close"] >= prev["Open"]
            and row["Open"] <= prev["Close"]
        )
        rejection = (
            row["lower_wick"] >= max(body, 1e-9) * config.rejection_wick_ratio
            and row["Close"] > row["Open"]
        )
        momentum = (
            pd.notna(atr)
            and atr > 0
            and body / atr >= config.momentum_body_atr_ratio
            and row["Close"] > row["Open"]
            and row["Close"] >= row["High"] - (0.25 * row["range_size"])
        )
    else:
        bearish_engulfing = (
            row["Close"] < row["Open"]
            and prev["Close"] > prev["Open"]
            and row["Open"] >= prev["Close"]
            and row["Close"] <= prev["Open"]
        )
        bullish_engulfing = bearish_engulfing
        rejection = (
            row["upper_wick"] >= max(body, 1e-9) * config.rejection_wick_ratio
            and row["Close"] < row["Open"]
        )
        momentum = (
            pd.notna(atr)
            and atr > 0
            and body / atr >= config.momentum_body_atr_ratio
            and row["Close"] < row["Open"]
            and row["Close"] <= row["Low"] + (0.25 * row["range_size"])
        )

    if bullish_engulfing:
        return "engulfing"
    if rejection:
        return "rejection_wick"
    if momentum:
        return "momentum_candle"
    return None


def build_signal_snapshot(symbol: str, market: str, df: pd.DataFrame) -> Optional[dict[str, Any]]:
    config = resolve_market_config(market)
    frame = compute_features(df, config)
    min_required = max(config.lookback_bars, config.trend_ma_period + 5) + 1
    if frame.empty or len(frame) < min_required:
        return None

    idx = len(frame) - 1
    row = frame.iloc[idx]
    bias = _trend_bias(row)
    if bias == "neutral":
        return None

    direction = "long" if bias == "bullish" else "short"
    trend_ok = True
    momentum_ok = _momentum_ok(row, direction, config)
    atr_ok = _atr_ok(row, config)
    pullback_ok, distance_atr = _pullback_ok(row, direction, config)
    sweep_ok, liquidity_level, sweep_level, trap_type = _find_sweep(frame, idx, direction, config)
    confirmation = _confirmation_type(frame, idx, direction, config)
    confirmation_ok = confirmation is not None

    score = StrategyScore(
        trend_alignment=2 if trend_ok else 0,
        momentum=2 if momentum_ok else 0,
        liquidity_sweep=2 if sweep_ok else 0,
        confirmation=2 if confirmation_ok else 0,
        clean_pullback=1 if pullback_ok else 0,
    )

    entry = float(row["Close"])
    atr = float(row["atr"]) if pd.notna(row["atr"]) else 0.0
    stop_anchor = sweep_level if sweep_level is not None else (float(row["Low"]) if direction == "long" else float(row["High"]))
    stop_buffer = max(atr * config.stop_buffer_atr, entry * config.stop_min_buffer_pct, 1e-6)
    stop_loss = stop_anchor - stop_buffer if direction == "long" else stop_anchor + stop_buffer
    risk = abs(entry - stop_loss)
    take_profit = entry + (risk * config.target_rr) if direction == "long" else entry - (risk * config.target_rr)
    rr = abs(take_profit - entry) / risk if risk > 0 else 0.0

    reasons: list[str] = []
    reasons.append(f"HTF trend bias is {bias} with price {'above' if direction == 'long' else 'below'} the 200 MA")
    reasons.append(f"20 MA slope is {row['ma_slope_pct']:.2f}% {'and passes' if momentum_ok else 'and is not strong enough for'} the momentum filter")
    reasons.append(f"ATR is {row['atr_pct'] * 100:.2f}% of price {'which passes' if atr_ok else 'which fails'} the volatility filter")
    reasons.append(
        f"Pullback distance is {distance_atr:.2f} ATR {'inside' if pullback_ok else 'outside'} the preferred 20 MA pullback band"
        if pd.notna(distance_atr) else
        "Pullback distance could not be measured"
    )
    reasons.append(
        f"Liquidity {'sweep found' if sweep_ok else 'sweep not confirmed'} near {sweep_level:.4f}" if sweep_level is not None else
        "Liquidity sweep not confirmed"
    )
    reasons.append(
        f"Price action confirmation is {confirmation.replace('_', ' ')}" if confirmation else
        "No engulfing, rejection wick, or momentum candle confirmation yet"
    )
    if trap_type:
        reasons.append(f"Trap logic note: {trap_type.replace('_', ' ')}")

    return {
        "symbol": symbol,
        "market": market,
        "timeframe": config.timeframe,
        "timestamp": frame.index[idx],
        "direction": direction,
        "bias": bias,
        "score": score,
        "entry": round(entry, 6),
        "stop_loss": round(float(stop_loss), 6),
        "take_profit": round(float(take_profit), 6),
        "risk_reward": round(rr, 2),
        "setup_type": "trend_pullback_liquidity_confirmation",
        "confirmation_type": confirmation,
        "liquidity_level": liquidity_level,
        "sweep_level": sweep_level,
        "trap_level": sweep_level if trap_type else None,
        "metrics": {
            "close": float(row["Close"]),
            "trend_ma": float(row["trend_ma"]),
            "signal_ma": float(row["signal_ma"]),
            "atr": atr,
            "atr_pct": float(row["atr_pct"]) if pd.notna(row["atr_pct"]) else None,
            "ma_slope_pct": float(row["ma_slope_pct"]) if pd.notna(row["ma_slope_pct"]) else None,
            "pullback_distance_atr": float(distance_atr) if pd.notna(distance_atr) else None,
        },
        "checks": {
            "trend_ok": trend_ok,
            "momentum_ok": momentum_ok,
            "atr_ok": atr_ok,
            "pullback_ok": pullback_ok,
            "sweep_ok": sweep_ok,
            "confirmation_ok": confirmation_ok,
        },
        "reasons": reasons,
        "qualified": bool(atr_ok and momentum_ok and pullback_ok and sweep_ok and confirmation_ok and score.total >= 5 and rr >= config.min_rr),
    }


def _find_sweep(frame: pd.DataFrame, idx: int, direction: str, config: MarketConfig) -> tuple[bool, Optional[float], Optional[float], Optional[str]]:
    liquidity = _find_latest_liquidity_levels(frame, idx - 1, config)
    trap_label: Optional[str] = None
    start_idx = max(config.swing_window + 2, idx - config.sweep_reversal_bars + 1)

    if direction == "long":
        level = liquidity["equal_low"] or liquidity["swing_low"]
        if not level:
            return False, None, None, None
        sweep_level = float(level["price"])
        for sweep_idx in range(start_idx, idx + 1):
            sweep_bar = frame.iloc[sweep_idx]
            current_bar = frame.iloc[idx]
            swept = sweep_bar["Low"] < sweep_level and sweep_bar["Close"] > sweep_level
            recovered = current_bar["Close"] >= sweep_bar["High"] or current_bar["Close"] > current_bar["signal_ma"]
            if swept and recovered:
                if current_bar["Close"] < sweep_level:
                    trap_label = "failed_sellside_reclaim"
                return True, sweep_level, sweep_level, trap_label
        return False, sweep_level, None, None

    level = liquidity["equal_high"] or liquidity["swing_high"]
    if not level:
        return False, None, None, None
    sweep_level = float(level["price"])
    for sweep_idx in range(start_idx, idx + 1):
        sweep_bar = frame.iloc[sweep_idx]
        current_bar = frame.iloc[idx]
        swept = sweep_bar["High"] > sweep_level and sweep_bar["Close"] < sweep_level
        recovered = current_bar["Close"] <= sweep_bar["Low"] or current_bar["Close"] < current_bar["signal_ma"]
        if swept and recovered:
            if current_bar["Close"] > sweep_level:
                trap_label = "failed_buyside_reject"
            return True, sweep_level, sweep_level, trap_label
    return False, sweep_level, None, None


def evaluate_signal(
    symbol: str,
    market: str,
    df: pd.DataFrame,
    *,
    signal_index: Optional[int] = None,
) -> Optional[TradeSignal]:
    snapshot = build_signal_snapshot(symbol, market, df)
    if snapshot is None or not snapshot["qualified"]:
        return None

    return TradeSignal(
        symbol=snapshot["symbol"],
        market=snapshot["market"],
        timeframe=snapshot["timeframe"],
        timestamp=snapshot["timestamp"],
        direction=snapshot["direction"],
        bias=snapshot["bias"],
        score=snapshot["score"],
        entry=snapshot["entry"],
        stop_loss=snapshot["stop_loss"],
        take_profit=snapshot["take_profit"],
        risk_reward=snapshot["risk_reward"],
        setup_type=snapshot["setup_type"],
        reasons=snapshot["reasons"],
        confirmation_type=snapshot["confirmation_type"],
        liquidity_level=snapshot["liquidity_level"],
        sweep_level=snapshot["sweep_level"],
        trap_level=snapshot["trap_level"],
        metrics=snapshot["metrics"],
    )


def evaluate_latest_signal(symbol: str, market: str, df: pd.DataFrame) -> Optional[TradeSignal]:
    return evaluate_signal(symbol, market, df, signal_index=None)


def generate_signal_series(symbol: str, market: str, df: pd.DataFrame) -> list[TradeSignal]:
    config = resolve_market_config(market)
    frame = compute_features(df, config)
    signals: list[TradeSignal] = []
    if frame.empty:
        return signals
    start = max(config.lookback_bars, config.trend_ma_period + 5)
    for idx in range(start, len(frame)):
        signal = evaluate_signal(symbol, market, frame.iloc[: idx + 1], signal_index=idx)
        if signal is not None:
            signals.append(signal)
    return signals


def run_backtest(
    symbol: str,
    market: str,
    df: pd.DataFrame,
    *,
    initial_capital: float = 10_000.0,
    risk_per_trade: float = 0.01,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = resolve_market_config(market)
    frame = compute_features(df, config)
    start_idx = max(config.lookback_bars, config.trend_ma_period + 5)
    min_required = start_idx + 1
    if frame.empty or len(frame) < min_required:
        raise ValueError("Not enough data to run the backtest.")

    equity = float(initial_capital)
    peak_equity = equity
    consecutive_losses = 0
    trades_today: dict[Any, int] = {}
    last_trade_idx = -10_000
    active_trade: Optional[dict[str, Any]] = None
    trade_log: list[BacktestTrade] = []
    equity_curve: list[dict[str, Any]] = [{"timestamp": frame.index[start_idx], "equity": equity}]
    daily_returns = deque(maxlen=3650)

    for idx in range(start_idx, len(frame)):
        row = frame.iloc[idx]
        timestamp = frame.index[idx]
        session_day = timestamp.date()

        if active_trade is not None:
            direction = active_trade["direction"]
            stop_loss = active_trade["stop_loss"]
            take_profit = active_trade["take_profit"]
            entry_price = active_trade["entry_price"]
            size = active_trade["position_size"]
            fees = active_trade["fees"]
            slippage = active_trade["slippage"]

            stop_hit = row["Low"] <= stop_loss if direction == "long" else row["High"] >= stop_loss
            target_hit = row["High"] >= take_profit if direction == "long" else row["Low"] <= take_profit

            exit_price = None
            outcome = None
            if stop_hit and target_hit:
                exit_price = stop_loss
                outcome = "stop_loss"
            elif stop_hit:
                exit_price = stop_loss
                outcome = "stop_loss"
            elif target_hit:
                exit_price = take_profit
                outcome = "take_profit"

            if exit_price is not None:
                gross_pnl = (exit_price - entry_price) * size if direction == "long" else (entry_price - exit_price) * size
                net_pnl = gross_pnl - fees - slippage
                equity += net_pnl
                peak_equity = max(peak_equity, equity)
                consecutive_losses = consecutive_losses + 1 if net_pnl < 0 else 0
                daily_returns.append(net_pnl / max(equity - net_pnl, 1e-9))
                trade_log.append(
                    BacktestTrade(
                        symbol=symbol,
                        market=market,
                        timeframe=config.timeframe,
                        direction=direction,
                        entry_time=active_trade["entry_time"],
                        exit_time=timestamp,
                        entry_price=round(entry_price, 6),
                        exit_price=round(exit_price, 6),
                        stop_loss=round(stop_loss, 6),
                        take_profit=round(take_profit, 6),
                        position_size=round(size, 8),
                        fees=round(fees, 6),
                        slippage=round(slippage, 6),
                        pnl=round(net_pnl, 6),
                        pnl_pct=round((net_pnl / max(active_trade["risk_amount"], 1e-9)) * 100, 2),
                        equity_after_trade=round(equity, 6),
                        risk_reward=round(active_trade["risk_reward"], 2),
                        score=active_trade["score"],
                        outcome=outcome,
                        reasons=active_trade["reasons"],
                    )
                )
                equity_curve.append({"timestamp": timestamp, "equity": equity})
                active_trade = None
            continue

        if consecutive_losses >= config.max_consecutive_losses:
            equity_curve.append({"timestamp": timestamp, "equity": equity})
            continue

        if idx - last_trade_idx < config.min_bars_between_trades:
            equity_curve.append({"timestamp": timestamp, "equity": equity})
            continue

        if trades_today.get(session_day, 0) >= config.max_trades_per_day:
            equity_curve.append({"timestamp": timestamp, "equity": equity})
            continue

        signal = evaluate_signal(symbol, market, frame.iloc[: idx + 1], signal_index=idx)
        if signal is None:
            equity_curve.append({"timestamp": timestamp, "equity": equity})
            continue

        risk_amount = equity * risk_per_trade
        risk_per_unit = abs(signal.entry - signal.stop_loss)
        if risk_per_unit <= 0:
            equity_curve.append({"timestamp": timestamp, "equity": equity})
            continue

        size = risk_amount / risk_per_unit
        notional = signal.entry * size
        fees = notional * config.fee_pct
        slippage = notional * config.slippage_pct
        entry_price = signal.entry * (1 + config.slippage_pct) if signal.direction == "long" else signal.entry * (1 - config.slippage_pct)

        active_trade = {
            "direction": signal.direction,
            "entry_time": timestamp,
            "entry_price": entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "position_size": size,
            "risk_reward": signal.risk_reward,
            "score": signal.score.total,
            "fees": fees,
            "slippage": slippage,
            "risk_amount": risk_amount,
            "reasons": signal.reasons,
        }
        trades_today[session_day] = trades_today.get(session_day, 0) + 1
        last_trade_idx = idx
        equity_curve.append({"timestamp": timestamp, "equity": equity})

    if active_trade is not None:
        last_row = frame.iloc[-1]
        timestamp = frame.index[-1]
        exit_price = float(last_row["Close"])
        direction = active_trade["direction"]
        gross_pnl = (exit_price - active_trade["entry_price"]) * active_trade["position_size"] if direction == "long" else (active_trade["entry_price"] - exit_price) * active_trade["position_size"]
        net_pnl = gross_pnl - active_trade["fees"] - active_trade["slippage"]
        equity += net_pnl
        trade_log.append(
            BacktestTrade(
                symbol=symbol,
                market=market,
                timeframe=config.timeframe,
                direction=direction,
                entry_time=active_trade["entry_time"],
                exit_time=timestamp,
                entry_price=round(active_trade["entry_price"], 6),
                exit_price=round(exit_price, 6),
                stop_loss=round(active_trade["stop_loss"], 6),
                take_profit=round(active_trade["take_profit"], 6),
                position_size=round(active_trade["position_size"], 8),
                fees=round(active_trade["fees"], 6),
                slippage=round(active_trade["slippage"], 6),
                pnl=round(net_pnl, 6),
                pnl_pct=round((net_pnl / max(active_trade["risk_amount"], 1e-9)) * 100, 2),
                equity_after_trade=round(equity, 6),
                risk_reward=round(active_trade["risk_reward"], 2),
                score=active_trade["score"],
                outcome="forced_exit",
                reasons=active_trade["reasons"],
            )
        )
        equity_curve.append({"timestamp": timestamp, "equity": equity})

    completed = [asdict(trade) for trade in trade_log]
    stats = _build_backtest_stats(completed, equity_curve, initial_capital, peak_equity, list(daily_returns))
    stats["config"] = {
        "market": config.market,
        "timeframe": config.timeframe,
        "atr_threshold_pct": config.atr_threshold_pct,
        "target_rr": config.target_rr,
        "max_trades_per_day": config.max_trades_per_day,
    }
    return completed, stats


def _build_backtest_stats(
    trades: list[dict[str, Any]],
    equity_curve: list[dict[str, Any]],
    initial_capital: float,
    peak_equity: float,
    returns: list[float],
) -> dict[str, Any]:
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "final_equity": round(initial_capital, 2),
            "equity_curve": equity_curve,
        }

    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]

    running_peak = initial_capital
    max_drawdown = 0.0
    for point in equity_curve:
        equity = point["equity"]
        running_peak = max(running_peak, equity)
        drawdown = 0.0 if running_peak == 0 else (running_peak - equity) / running_peak
        max_drawdown = max(max_drawdown, drawdown)

    returns_series = pd.Series(returns, dtype=float)
    sharpe = 0.0
    if len(returns_series) > 1 and returns_series.std(ddof=0) > 0:
        sharpe = float((returns_series.mean() / returns_series.std(ddof=0)) * sqrt(252))

    final_equity = equity_curve[-1]["equity"] if equity_curve else initial_capital
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round((len(wins) / len(trades)) * 100, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
        "max_drawdown": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "final_equity": round(final_equity, 2),
        "net_profit": round(final_equity - initial_capital, 2),
        "return_pct": round(((final_equity - initial_capital) / initial_capital) * 100, 2),
        "average_rr": round(float(np.mean([trade["risk_reward"] for trade in trades])), 2),
        "avg_confluence_score": round(float(np.mean([trade["score"] for trade in trades])), 2),
        "equity_curve": equity_curve,
        "peak_equity": round(peak_equity, 2),
    }
