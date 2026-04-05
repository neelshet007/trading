from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from trading_engine import normalize_ohlcv, run_backtest


logger = logging.getLogger(__name__)
YFINANCE_BACKTEST_TIMEOUT_SECONDS = 12


def _legacy_trade_log(trades: list[dict], stats: dict) -> list[dict]:
    converted: list[dict] = []
    for trade in trades:
        entry_time = str(trade.get("entry_time", ""))
        exit_time = str(trade.get("exit_time", ""))
        direction = str(trade.get("direction", "")).upper()
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        outcome = str(trade.get("outcome", ""))
        converted.append(
            {
                "date_time": entry_time,
                "market_context": f"{trade.get('market', '')} | {trade.get('timeframe', '')} | Score {trade.get('score', 0)}",
                "trade_type": "Swing",
                "direction": direction,
                "trigger_why": " | ".join(trade.get("reasons", [])),
                "entry_price": trade.get("entry_price"),
                "stop_loss": trade.get("stop_loss"),
                "target": trade.get("take_profit"),
                "exit_price": trade.get("exit_price"),
                "risk_reward": trade.get("risk_reward"),
                "pnl_pct": trade.get("pnl_pct"),
                "pnl_dollars": pnl,
                "account_equity": trade.get("equity_after_trade"),
                "result": "Target Hit ✅" if outcome == "take_profit" else "Stopped ❌" if outcome == "stop_loss" else "Closed ⏳",
                "confluence_score": trade.get("score"),
                "trade_balance_before": (trade.get("equity_after_trade") or 0) - pnl,
                "dollar_risk": abs((trade.get("entry_price") or 0) - (trade.get("stop_loss") or 0)) * (trade.get("position_size") or 0),
                "position_size": trade.get("position_size"),
                "exit_time": exit_time,
            }
        )
    return converted


def _legacy_stats(stats: dict) -> dict:
    return {
        **stats,
        "win_rate_pct": stats.get("win_rate", 0.0),
        "max_drawdown_pct": stats.get("max_drawdown", 0.0),
        "max_drawdown_usd": round((stats.get("peak_equity", 0.0) - stats.get("final_equity", 0.0)), 2),
        "total_return_pct": stats.get("return_pct", 0.0),
        "final_equity_usd": stats.get("final_equity", 0.0),
        "buy_hold_return_pct": 0.0,
        "alpha_vs_bnh_pct": stats.get("return_pct", 0.0),
        "avg_confluence_score": stats.get("avg_confluence_score", 0.0),
    }


def infer_market_from_symbol(symbol: str) -> str:
    upper = symbol.upper()
    if "-USD" in upper or upper.endswith("USD"):
        return "CRYPTO" if "-" in upper else "FOREX"
    if upper.endswith("=F"):
        return "COMMODITIES"
    return "STOCKS"


def resolve_backtest_interval(start: str, end: str) -> str:
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return "1h"

    days = max((end_dt - start_dt).days, 1)
    if days > 729:
        return "1d"
    return "1h"


def _download(symbol: str, interval: str, start: str, end: str) -> Optional[pd.DataFrame]:
    try:
        logger.info("Downloading backtest data for %s interval=%s start=%s end=%s", symbol, interval, start, end)
        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=YFINANCE_BACKTEST_TIMEOUT_SECONDS,
        )
        if df is None or df.empty:
            return None
        return normalize_ohlcv(df)
    except Exception as exc:
        logger.error("Backtest download failed for %s: %s", symbol, exc)
        return None


def run_smc_backtest(
    symbol: str = "BTC-USD",
    start: str = "2023-01-01",
    end: str = "2025-12-31",
    initial_capital: float = 10000.0,
    market: Optional[str] = None,
) -> tuple[list[dict], dict]:
    resolved_market = market or infer_market_from_symbol(symbol)
    interval = resolve_backtest_interval(start, end)
    df = _download(symbol, interval, start, end)
    if df is None or df.empty:
        raise ValueError(f"Unable to fetch data for {symbol}.")

    trades, stats = run_backtest(
        symbol=symbol,
        market=resolved_market,
        df=df,
        initial_capital=initial_capital,
        risk_per_trade=0.01,
    )
    legacy_trades = _legacy_trade_log(trades, stats)
    legacy_stats = _legacy_stats(stats)
    legacy_stats["symbol"] = symbol
    legacy_stats["market"] = resolved_market
    legacy_stats["start"] = start
    legacy_stats["end"] = end
    legacy_stats["interval_used"] = interval
    return legacy_trades, legacy_stats


def generate_excel_report(trades: list[dict], stats: dict, symbol: str) -> bytes:
    try:
        import openpyxl
        from openpyxl.chart import LineChart, Reference
        from openpyxl.styles import Font
    except ImportError as exc:
        raise ImportError("openpyxl required. Run: pip install openpyxl") from exc

    workbook = openpyxl.Workbook()
    trade_sheet = workbook.active
    trade_sheet.title = "Trades"

    if trades:
        trade_headers = list(trades[0].keys())
        trade_sheet.append(trade_headers)
        for cell in trade_sheet[1]:
            cell.font = Font(bold=True)
        for trade in trades:
            trade_sheet.append([trade.get(header) for header in trade_headers])
    else:
        trade_sheet.append(["message"])
        trade_sheet.append(["No trades generated"])

    stats_sheet = workbook.create_sheet("Stats")
    for idx, (key, value) in enumerate(stats.items(), start=1):
        if key == "equity_curve":
            continue
        stats_sheet.cell(row=idx, column=1, value=key)
        stats_sheet.cell(row=idx, column=2, value=str(value))
    stats_sheet["A1"].font = Font(bold=True)

    curve_sheet = workbook.create_sheet("EquityCurve")
    curve_sheet.append(["timestamp", "equity"])
    equity_curve = stats.get("equity_curve", [])
    for point in equity_curve:
        curve_sheet.append([str(point.get("timestamp")), point.get("equity")])

    if len(equity_curve) > 1:
        chart = LineChart()
        chart.title = f"Equity Curve - {symbol}"
        chart.y_axis.title = "Equity"
        chart.x_axis.title = "Bar"
        data = Reference(curve_sheet, min_col=2, min_row=1, max_row=len(equity_curve) + 1)
        chart.add_data(data, titles_from_data=True)
        categories = Reference(curve_sheet, min_col=1, min_row=2, max_row=len(equity_curve) + 1)
        chart.set_categories(categories)
        curve_sheet.add_chart(chart, "D2")

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()
