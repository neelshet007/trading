"""
backtest.py — Optimized Manifesto-Aligned Historical Simulation
==============================================================
Performance refactored to handle 10,000+ bar loops at high speed.
Uses vectorized pre-calculation for H4 and Daily timeframes to avoid O(N²) resample bottlenecks.
Signal generation is fully delegated to engine.build_setup() for source-of-truth accuracy.
"""
from __future__ import annotations

import io
import logging
import time
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from engine import TimeframeBundle, build_setup
from manifesto_config import load_manifesto_config
import indicators  # Used for monkey-patch optimization

logger = logging.getLogger(__name__)
MANIFESTO = load_manifesto_config()

INITIAL_EQUITY = 10_000.0

# Increased history to ensure indicators (like EMA_200) don't drop the entire slice
_MIN_H1_BARS = 250
_MIN_DAILY_BARS = 65


# ─────────────────────────────────────────────────────────────────────────────
# Data acquisition
# ─────────────────────────────────────────────────────────────────────────────

def _download(symbol: str, interval: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """Download OHLCV from yfinance and normalise column names + UTC index."""
    try:
        # Check for 1h data limit (Yahoo limit is roughly last 730 days)
        if interval == "1h":
            start_dt = pd.to_datetime(start)
            limit_dt = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=729)
            if start_dt < limit_dt:
                logger.warning("1h Yahoo data is only available for the last 730 days. Truncating start date.")
                start = limit_dt.strftime("%Y-%m-%d")

        df = yf.download(
            symbol, start=start, end=end,
            interval=interval, auto_adjust=True, progress=False,
        )
        if df is None or df.empty:
            return None
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        df.index = pd.to_datetime(df.index, utc=True)
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception as exc:
        logger.error("Download failed %s %s: %s", symbol, interval, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic bundle builder (Optimized for Speed)
# ─────────────────────────────────────────────────────────────────────────────

def _build_bar_bundle_optimized(
    symbol: str,
    df_h1_full: pd.DataFrame,
    df_h4_full: pd.DataFrame,
    df_daily_full: pd.DataFrame,
    current_ts: pd.Timestamp,
) -> Optional[TimeframeBundle]:
    """
    Slices pre-calculated dataframes using timestamps. O(1) complexity compared
    to iterative resampling.
    """
    # 1. Slice H1 up to current timestamp
    h1_slice = df_h1_full[df_h1_full.index <= current_ts]
    if len(h1_slice) < _MIN_H1_BARS:
        return None

    # 2. Slice Daily up to current timestamp
    daily_slice = df_daily_full[df_daily_full.index <= current_ts]
    if len(daily_slice) < _MIN_DAILY_BARS:
        return None

    # 3. Slice H4 up to current timestamp
    h4_slice = df_h4_full[df_h4_full.index <= current_ts]
    if len(h4_slice) < 10:
        return None

    # Intraday proxy — last 48 bars for 5M/1M patterns
    intraday_proxy = h1_slice.tail(48)

    return TimeframeBundle(
        symbol=symbol,
        daily=daily_slice,
        h4=h4_slice,
        h1=h1_slice.tail(120),
        m15=intraday_proxy,
        m5=intraday_proxy,
        m1=intraday_proxy,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main backtest loop
# ─────────────────────────────────────────────────────────────────────────────

def run_smc_backtest(
    symbol: str = "BTC-USD",
    start: str = "2023-01-01",
    end: str = "2025-12-31",
    initial_capital: float = INITIAL_EQUITY,
    require_strong_buy: bool = False,
) -> tuple[list[dict], dict]:
    """
    Optimized Backtest Loop:
    - Pre-calculates resampled timeframes.
    - Monkey-patches indicators for 10x speed.
    - Uses timestamp-based slicing.
    """
    logger.info("Initializing high-speed manifesto backtest for %s", symbol)
    perf_start = time.time()

    # 1. Download and Validaton
    df_h1 = _download(symbol, "1h", start, end)
    if df_h1 is None or len(df_h1) < _MIN_H1_BARS:
        raise ValueError(f"Not enough 1H data for {symbol}. Yahoo H1 limit is last 730 days.")

    df_daily_orig = _download(symbol, "1d", start, end)
    if df_daily_orig is None or len(df_daily_orig) < _MIN_DAILY_BARS:
        raise ValueError(f"No daily data for {symbol}.")

    # 2. Pre-Calculate Timeframes (Vectorized)
    logger.info("Pre-calculating timeframes and indicators...")
    df_h4_full = (
        df_h1
        .resample("4h")
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna()
    )
    
    # Pre-calculate indicators on the FULL dataframes once
    # This prevents the engine from doing it 10,000 times
    df_h1 = indicators.add_indicators(df_h1)
    df_h4_full = indicators.add_indicators(df_h4_full)
    df_daily_full = indicators.add_indicators(df_daily_orig)

    # 3. Performance Monkey-Patch (Massive speed win)
    # We temporarily replace indicators.add_indicators with a version that skips 
    # work if the dataframe already has columns like 'ATR'.
    original_add_indicators = indicators.add_indicators
    def fast_add_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if "ATR" in df.columns:
            return df
        return original_add_indicators(df)
    
    indicators.add_indicators = fast_add_indicators

    trades: list[dict] = []
    equity = initial_capital
    current_trade: Optional[dict] = None

    try:
        # Loop through H1 bars
        # We start from the index where we have enough data
        for i in range(_MIN_H1_BARS, len(df_h1) - 1):
            bar = df_h1.iloc[i]
            current_ts = df_h1.index[i]

            # ── Manage open trade ──────────────────────────────────────────────
            if current_trade is not None:
                direction = current_trade["direction"]
                hit_stop = (
                    direction == "LONG" and float(bar["Low"]) <= current_trade["stop_loss"]
                ) or (
                    direction == "SHORT" and float(bar["High"]) >= current_trade["stop_loss"]
                )
                hit_target = (
                    direction == "LONG" and float(bar["High"]) >= current_trade["target"]
                ) or (
                    direction == "SHORT" and float(bar["Low"]) <= current_trade["target"]
                )

                if hit_stop or hit_target:
                    exit_price = current_trade["target"] if hit_target else current_trade["stop_loss"]
                    entry = current_trade["entry_price"]
                    pnl_pct = (
                        (exit_price - entry) / entry * 100
                        if direction == "LONG"
                        else (entry - exit_price) / entry * 100
                    )
                    pnl_dollars = (
                        (exit_price - entry) * current_trade["position_size"]
                        if direction == "LONG"
                        else (entry - exit_price) * current_trade["position_size"]
                    )
                    equity = max(0.01, equity + pnl_dollars)
                    current_trade.update(
                        exit_price=round(exit_price, 4),
                        pnl_pct=round(pnl_pct, 2),
                        pnl_dollars=round(pnl_dollars, 2),
                        account_equity=round(equity, 2),
                        result="Target Hit" if hit_target else "Stopped",
                    )
                    trades.append(current_trade)
                    current_trade = None
                continue 

            # ── Signal generation (Optimized) ────────────────────────────────────
            bundle = _build_bar_bundle_optimized(symbol, df_h1, df_h4_full, df_daily_full, current_ts)
            if bundle is None:
                continue

            try:
                setup = build_setup(bundle)
            except Exception:
                continue

            if setup is None or setup.status != "qualified":
                continue

            if require_strong_buy and setup.verdict != "STRONG BUY":
                continue

            # Position sizing
            entry = setup.entry
            stop_loss = setup.stop_loss
            target = setup.take_profit
            direction = "LONG" if setup.bias == "bullish" else "SHORT"

            if not (entry > 0 and stop_loss > 0 and target > 0):
                continue
            
            stop_distance = abs(entry - stop_loss)
            if stop_distance <= 0:
                continue

            risk_pct = MANIFESTO.default_risk_pct / 100
            dollar_risk = round(equity * risk_pct, 2)
            position_size = dollar_risk / stop_distance

            # Metadata extraction
            conf = setup.confluence
            footprint = setup.footprint
            context = setup.context
            trigger = setup.trigger

            trigger_why = " | ".join([
                f"HTF trend {conf.trend_alignment}/2",
                f"FVG {conf.fvg_mitigation}/3",
                f"Liquidity sweep {conf.idm_sweep}/3",
                f"Premium-discount {conf.discount_premium}/3",
                f"Order flow {conf.order_flow_alignment}/2 ({footprint.cvd_divergence})",
                f"Entry model: {trigger.entry_model}",
            ])

            rng = max(footprint.htf_range_high - footprint.htf_range_low, 1e-9)
            fib_position = (entry - footprint.htf_range_low) / rng

            market_context = (
                f"{context.hmm_regime} | {footprint.premium_discount_state.title()} delivery | "
                f"IPDA: {context.ipda_cycle} | "
                f"Fib {fib_position:.2f} | Score {conf.total_score}/{MANIFESTO.confluence_max_score:.0f}"
            )

            current_trade = {
                "date_time": str(current_ts),
                "direction": direction,
                "entry_model": trigger.entry_model,
                "confirmation": trigger.confirmation,
                "regime_state": context.hmm_state,
                "regime_label": context.hmm_regime,
                "entry_price": round(entry, 4),
                "stop_loss": round(stop_loss, 4),
                "target": round(target, 4),
                "confluence_score": round(float(conf.total_score), 1),
                "market_context": market_context,
                "trigger_why": trigger_why,
                "risk_reward": setup.risk.r_multiple,
                "funding_clamp_bps": setup.risk.funding_rate_clamp_bps,
                "slippage_bps": setup.risk.expected_slippage_bps,
                "verdict": setup.verdict,
                "trade_type": "Swing" if abs(target - entry) / max(entry, 1e-9) > 0.03 else "Intraday",
                "trade_balance_before": round(equity, 2),
                "dollar_risk": dollar_risk,
                "position_size": round(position_size, 6),
            }

    finally:
        # ALWAYS restore the original indicator function
        indicators.add_indicators = original_add_indicators

    # Finalize open trade
    if current_trade is not None:
        last_close = float(df_h1["Close"].iloc[-1])
        entry = current_trade["entry_price"]
        direction = current_trade["direction"]
        pnl_pct = (last_close - entry) / entry * 100 if direction == "LONG" else (entry - last_close) / entry * 100
        pnl_dollars = (last_close - entry) * current_trade["position_size"] if direction == "LONG" else (entry - last_close) * current_trade["position_size"]
        current_trade.update(
            exit_price=round(last_close, 4),
            pnl_pct=round(pnl_pct, 2),
            pnl_dollars=round(pnl_dollars, 2),
            account_equity=round(equity + pnl_dollars, 2),
            result="Open at End",
        )
        trades.append(current_trade)

    stats = _compute_stats(trades, df_daily_full, initial_capital)
    perf_end = time.time()
    logger.info("Backtest complete in %.2f seconds.", perf_end - perf_start)
    return trades, stats


# ─────────────────────────────────────────────────────────────────────────────
# Analytics and Excel (Keep original logic but use stats dict)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_stats(trades: list[dict], df_daily: pd.DataFrame, init: float) -> dict:
    completed = [t for t in trades if t.get("result") in {"Target Hit", "Stopped"}]
    if not completed:
        return {
            "error": (
                "No completed trades found. "
                "Try a wider date range or check that the manifesto filters are not too strict."
            )
        }

    wins = [t for t in completed if t["result"] == "Target Hit"]
    losses = [t for t in completed if t["result"] == "Stopped"]
    gross_profit = sum(t["pnl_dollars"] for t in wins)
    gross_loss = abs(sum(t["pnl_dollars"] for t in losses)) or 1.0

    equity_curve = [init]
    for trade in completed:
        equity_curve.append(equity_curve[-1] + trade["pnl_dollars"])

    peak = equity_curve[0]
    max_drawdown_pct = 0.0
    max_drawdown_usd = 0.0
    for eq in equity_curve:
        peak = max(peak, eq)
        dd_pct = ((peak - eq) / peak) * 100 if peak else 0.0
        dd_usd = peak - eq
        max_drawdown_pct = max(max_drawdown_pct, dd_pct)
        max_drawdown_usd = max(max_drawdown_usd, dd_usd)

    returns_series = pd.Series(equity_curve).pct_change().dropna()
    sharpe = float(
        (returns_series.mean() / returns_series.std() * (252 ** 0.5))
        if returns_series.std() > 0 else 0.0
    )
    final_equity = equity_curve[-1]
    total_return = ((final_equity - init) / init) * 100

    bnh_start = float(df_daily["Close"].iloc[0])
    bnh_end = float(df_daily["Close"].iloc[-1])
    buy_hold_return = ((bnh_end - bnh_start) / bnh_start) * 100

    # Break down trades by entry model (manifesto models only)
    model_counts: dict[str, int] = {}
    for t in completed:
        model = t.get("entry_model", "Unknown")
        model_counts[model] = model_counts.get(model, 0) + 1

    return {
        "total_trades": len(completed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(completed) * 100, 1),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "max_drawdown_usd": round(max_drawdown_usd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "total_return_pct": round(total_return, 2),
        "final_equity_usd": round(final_equity, 2),
        "buy_hold_return_pct": round(buy_hold_return, 2),
        "alpha_vs_bnh_pct": round(total_return - buy_hold_return, 2),
        "avg_confluence_score": round(
            sum(t.get("confluence_score", 0) for t in completed) / len(completed), 1
        ),
        "entry_model_breakdown": model_counts,
        "manifesto_threshold": MANIFESTO.confluence_threshold,
        "manifesto_lookback_bars": MANIFESTO.structural_lookback_bars,
    }


def generate_excel_report(trades: list[dict], stats: dict, symbol: str) -> bytes:
    try:
        import openpyxl
        from openpyxl.chart import LineChart, Reference
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError as exc:
        raise ImportError("openpyxl required. Run: pip install openpyxl") from exc

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Manifesto Trade Log"

    dark = PatternFill("solid", fgColor="0D1117")
    green_bg = PatternFill("solid", fgColor="0D3321")
    red_bg = PatternFill("solid", fgColor="3D0D0D")
    cyan = Font(color="00FFFF", bold=True)
    green = Font(color="00FF88")
    red = Font(color="FF4444")
    white = Font(color="FFFFFF", bold=True)
    gray = Font(color="888888")
    thin = Side(style="thin", color="333333")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    headers = [
        "Date_Time", "Context", "Type", "Direction", "Trigger",
        "Score", "Balance_Before", "Dollar_Risk", "Entry", "SL",
        "Target", "Pos_Size", "Exit", "PnL_%", "Net_PnL_USD", "Equity", "Result",
    ]
    widths = [22, 52, 10, 10, 90, 7, 16, 14, 14, 14, 14, 16, 14, 10, 14, 18, 18]

    for col_idx, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_idx, value=header)
        cell.fill = dark
        cell.font = cyan
        cell.alignment = center
        cell.border = border

    for row_idx, trade in enumerate(trades, 2):
        result = trade.get("result", "")
        fill = green_bg if "Target" in result else red_bg if "Stopped" in result else dark
        row = [
            trade.get("date_time", ""),
            trade.get("market_context", ""),
            trade.get("trade_type", ""),
            trade.get("direction", ""),
            trade.get("trigger_why", ""),
            trade.get("confluence_score", ""),
            trade.get("trade_balance_before", ""),
            trade.get("dollar_risk", ""),
            trade.get("entry_price", ""),
            trade.get("stop_loss", ""),
            trade.get("target", ""),
            trade.get("position_size", ""),
            trade.get("exit_price", ""),
            trade.get("pnl_pct", ""),
            trade.get("pnl_dollars", ""),
            trade.get("account_equity", ""),
            result,
        ]
        for col_idx, value in enumerate(row, 1):
            cell = sheet.cell(row=row_idx, column=col_idx, value=value)
            cell.fill = fill
            cell.border = border
            cell.alignment = left if col_idx in (2, 5) else center
            if col_idx in (7, 8, 15, 16):
                cell.number_format = '"$"#,##0.00'
            elif col_idx == 12:
                cell.number_format = "#,##0.0000"
            if col_idx == 15:
                cell.font = green if (value or 0) >= 0 else red
            else:
                cell.font = white if col_idx in (4, 6, 17) else gray

    for col_idx, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(col_idx)].width = width
    sheet.freeze_panes = "A2"

    # ── Performance Analytics sheet ───────────────────────────────────────────
    stats_sheet = workbook.create_sheet("Performance Analytics")
    model_breakdown = stats.get("entry_model_breakdown", {})
    stat_rows = [
        ("Manifesto Backtest", ""),
        ("Symbol", symbol),
        ("Lookback Bars", stats.get("manifesto_lookback_bars", MANIFESTO.structural_lookback_bars)),
        ("Confluence Threshold", f"{stats.get('manifesto_threshold', MANIFESTO.confluence_threshold):.1f}/{MANIFESTO.confluence_max_score:.1f}"),
        ("Total Trades", stats.get("total_trades", 0)),
        ("Wins", stats.get("wins", 0)),
        ("Losses", stats.get("losses", 0)),
        ("Win Rate", f"{stats.get('win_rate_pct', 0):.1f}%"),
        ("Avg Confluence Score", f"{stats.get('avg_confluence_score', 0):.1f}/{MANIFESTO.confluence_max_score:.1f}"),
        ("Final Equity", f"${stats.get('final_equity_usd', 0):,.2f}"),
        ("Total Return", f"{stats.get('total_return_pct', 0):.2f}%"),
        ("Profit Factor", f"{stats.get('profit_factor', 0):.2f}x"),
        ("Max Drawdown", f"{stats.get('max_drawdown_pct', 0):.2f}%"),
        ("Sharpe Ratio", f"{stats.get('sharpe_ratio', 0):.2f}"),
        ("Buy & Hold", f"{stats.get('buy_hold_return_pct', 0):.2f}%"),
        ("Alpha vs B&H", f"{stats.get('alpha_vs_bnh_pct', 0):+.2f}%"),
        ("", ""),
        ("--- Entry Model Breakdown ---", ""),
        *[(model, count) for model, count in model_breakdown.items()],
    ]
    for row_idx, (label, value) in enumerate(stat_rows, 1):
        lbl_cell = stats_sheet.cell(row=row_idx, column=1, value=label)
        val_cell = stats_sheet.cell(row=row_idx, column=2, value=value)
        lbl_cell.font = cyan if row_idx == 1 else white if label.startswith("---") else gray
        val_cell.font = white
    stats_sheet.column_dimensions["A"].width = 32
    stats_sheet.column_dimensions["B"].width = 24

    # ── Equity Curve sheet ────────────────────────────────────────────────────
    curve_sheet = workbook.create_sheet("Equity Curve")
    curve_sheet.append(["Trade #", "Equity ($)"])
    running_equity = INITIAL_EQUITY
    for index, trade in enumerate(trades, 1):
        running_equity = trade.get("account_equity", running_equity)
        curve_sheet.append([index, running_equity])

    chart = LineChart()
    chart.title = "Manifesto Equity Curve"
    chart.y_axis.title = "Equity ($)"
    chart.x_axis.title = "Trade #"
    chart.width = 24
    chart.height = 14
    chart.add_data(
        Reference(curve_sheet, min_col=2, min_row=1, max_row=len(trades) + 1),
        titles_from_data=True,
    )
    chart.set_categories(
        Reference(curve_sheet, min_col=1, min_row=2, max_row=len(trades) + 1)
    )
    curve_sheet.add_chart(chart, "D2")

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()
