"""
SMC + Technical Confluence Blind Backtester
Strategy:
  SMC Core   : Liquidity Sweeps (SSL/BSL), BOS, FVG (unmitigated), Order Blocks
  Technical  : 20 EMA trend filter, RSI (oversold/overbought), MACD histogram direction
  Grade A+ setup requires ALL confluence layers aligned.
"""
import io
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Optional

logger = logging.getLogger(__name__)

INITIAL_EQUITY = 10_000.0
RISK_PER_TRADE = 0.01          # 1% risk per trade
RR_LONG        = 3.0           # 1:3 on longs (SMC swing targets)
RR_SHORT       = 3.0
MIN_SCORE      = 5             # minimum confluence score to take trade (max possible = 8)

# ─────────────────────────────────────────────
# DATA LAYER
# ─────────────────────────────────────────────
def _download(symbol: str, interval: str, start: str, end: str) -> Optional[pd.DataFrame]:
    try:
        df = yf.download(symbol, start=start, end=end, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df.index   = pd.to_datetime(df.index, utc=True)
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception as e:
        logger.error("Download failed %s %s: %s", symbol, interval, e)
        return None


# ─────────────────────────────────────────────
# INDICATOR CALCULATIONS
# ─────────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # ── SMC layers ──────────────────────────────────────────────────────
    # Liquidity Sweeps (rolling 48-bar = ~2 trading days on 1H)
    lb = 48
    df["roll_hi"] = df["High"].shift(1).rolling(lb).max()
    df["roll_lo"] = df["Low"].shift(1).rolling(lb).min()
    df["bsl_sweep"] = (df["High"] > df["roll_hi"]) & (df["Close"] < df["roll_hi"])
    df["ssl_sweep"] = (df["Low"]  < df["roll_lo"]) & (df["Close"] > df["roll_lo"])
    df["sweep_lo_level"] = np.where(df["ssl_sweep"], df["roll_lo"], np.nan)
    df["sweep_hi_level"] = np.where(df["bsl_sweep"], df["roll_hi"], np.nan)

    # Fair Value Gaps
    h2, l0 = df["High"].shift(2), df["Low"]
    l2, h0 = df["Low"].shift(2),  df["High"]
    df["fvg_bull_top"] = np.where(h2 < l0, l0, np.nan)
    df["fvg_bull_bot"] = np.where(h2 < l0, h2, np.nan)
    df["fvg_bear_top"] = np.where(l2 > h0, l2, np.nan)
    df["fvg_bear_bot"] = np.where(l2 > h0, h0, np.nan)

    # BOS
    df["swing_hi"] = df["High"].rolling(20).max().shift(1)
    df["swing_lo"] = df["Low"].rolling(20).min().shift(1)
    df["bos_bull"] = df["Close"] > df["swing_hi"]
    df["bos_bear"] = df["Close"] < df["swing_lo"]

    # ── Technical confluence ─────────────────────────────────────────────
    # 20 EMA
    df["ema20"] = df["Close"].ewm(span=20, adjust=False).mean()

    # RSI-14
    delta  = df["Close"].diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta.clip(upper=0)).rolling(14).mean()
    rs     = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD (12,26,9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd_hist"] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()

    # 50 SMA (daily bias on the 1H chart as htf proxy)
    df["sma50"] = df["Close"].rolling(50).mean()

    return df


def fib_pos(close: float, hi: float, lo: float) -> float:
    rng = hi - lo
    return (close - lo) / rng if rng > 0 else 0.5


# ─────────────────────────────────────────────
# CONFLUENCE SCORER
# ─────────────────────────────────────────────
def score_long(bar: pd.Series, prev_bar: pd.Series, close: float,
               hi20: float, lo20: float, fvg_bull: list) -> tuple[int, list[str]]:
    """Return (score, reasons). Max score = 8."""
    score = 0
    reasons = []

    # 1. HTF bias: price above 50 SMA (+1)
    if pd.notna(bar["sma50"]) and close > bar["sma50"]:
        score += 1; reasons.append("HTF Bias ✅ Price > 50 SMA")

    # 2. 20 EMA trending up — close above ema20 (+1)
    if pd.notna(bar["ema20"]) and close > bar["ema20"]:
        score += 1; reasons.append("EMA20 Filter ✅ Price above 20 EMA")

    # 3. RSI oversold recovery — RSI was < 40 and now rising back above 40 (+2)
    rsi = bar["rsi"] if pd.notna(bar["rsi"]) else 50
    prev_rsi = prev_bar["rsi"] if pd.notna(prev_bar["rsi"]) else 50
    if rsi > 40 and prev_rsi < 40:
        score += 2; reasons.append("RSI ✅ Oversold recovery (crossed 40↑)")
    elif rsi < 55:
        score += 1; reasons.append("RSI ✅ Not overbought (< 55)")

    # 4. MACD histogram turning positive (+1)
    if pd.notna(bar["macd_hist"]) and bar["macd_hist"] > 0 and pd.notna(prev_bar["macd_hist"]) and prev_bar["macd_hist"] <= 0:
        score += 1; reasons.append("MACD ✅ Histogram turned positive")

    # 5. SSL sweep detected on this or prior bar (+1)
    if bar["ssl_sweep"] or prev_bar["ssl_sweep"]:
        score += 1; reasons.append("SSL ✅ Sell-Side Liquidity swept")

    # 6. BOS bullish (+1)
    if bar["bos_bull"]:
        score += 1; reasons.append("BOS ✅ Bullish Break of Structure")

    # 7. Unmitigated Bull FVG exists (+1)
    if fvg_bull:
        score += 1; reasons.append(f"FVG ✅ Unmitigated Bull FVG at {round(fvg_bull[-1][0],2)}")

    # 8. Price in discount zone (below 0.5 Fib) (+1)
    fp = fib_pos(close, hi20, lo20)
    if fp < 0.5:
        score += 1; reasons.append(f"Zone ✅ Discount zone (Fib {fp:.2f})")

    return score, reasons


def score_short(bar: pd.Series, prev_bar: pd.Series, close: float,
                hi20: float, lo20: float, fvg_bear: list) -> tuple[int, list[str]]:
    """Return (score, reasons). Max score = 8."""
    score = 0
    reasons = []

    # 1. HTF bias: price below 50 SMA (+1)
    if pd.notna(bar["sma50"]) and close < bar["sma50"]:
        score += 1; reasons.append("HTF Bias ✅ Price < 50 SMA")

    # 2. 20 EMA trending down (+1)
    if pd.notna(bar["ema20"]) and close < bar["ema20"]:
        score += 1; reasons.append("EMA20 Filter ✅ Price below 20 EMA")

    # 3. RSI overbought rejection — RSI was > 60 and now falling below 60 (+2)
    rsi = bar["rsi"] if pd.notna(bar["rsi"]) else 50
    prev_rsi = prev_bar["rsi"] if pd.notna(prev_bar["rsi"]) else 50
    if rsi < 60 and prev_rsi > 60:
        score += 2; reasons.append("RSI ✅ Overbought rejection (crossed 60↓)")
    elif rsi > 45:
        score += 1; reasons.append("RSI ✅ Not oversold (> 45)")

    # 4. MACD histogram turning negative (+1)
    if pd.notna(bar["macd_hist"]) and bar["macd_hist"] < 0 and pd.notna(prev_bar["macd_hist"]) and prev_bar["macd_hist"] >= 0:
        score += 1; reasons.append("MACD ✅ Histogram turned negative")

    # 5. BSL sweep (+1)
    if bar["bsl_sweep"] or prev_bar["bsl_sweep"]:
        score += 1; reasons.append("BSL ✅ Buy-Side Liquidity swept")

    # 6. BOS bearish (+1)
    if bar["bos_bear"]:
        score += 1; reasons.append("BOS ✅ Bearish Break of Structure")

    # 7. Unmitigated Bear FVG (+1)
    if fvg_bear:
        score += 1; reasons.append(f"FVG ✅ Unmitigated Bear FVG at {round(fvg_bear[-1][0],2)}")

    # 8. Price in premium zone (above 0.5 Fib) (+1)
    fp = fib_pos(close, hi20, lo20)
    if fp > 0.5:
        score += 1; reasons.append(f"Zone ✅ Premium zone (Fib {fp:.2f})")

    return score, reasons


# ─────────────────────────────────────────────
# MAIN BACKTEST ENGINE
# ─────────────────────────────────────────────
def run_smc_backtest(
    symbol: str = "BTC-USD",
    start:  str = "2023-01-01",
    end:    str = "2025-12-31",
    initial_capital: float = 10000.0,
) -> tuple[list[dict], dict]:

    logger.info("Starting SMC+TA backtest for %s (%s → %s)", symbol, start, end)

    df = _download(symbol, "1h", start, end)
    if df is None or len(df) < 100:
        raise ValueError(f"Not enough 1H data for {symbol}.")

    df_daily = _download(symbol, "1d", start, end)
    if df_daily is None or df_daily.empty:
        raise ValueError(f"No daily data for {symbol}.")

    df = add_indicators(df)

    trades    : list[dict] = []
    equity    : float      = initial_capital
    in_trade  : bool       = False
    cur_trade : Optional[dict] = None

    # Live FVG tracking lists — (top, bot, timestamp)
    fvg_bull: list[tuple] = []
    fvg_bear: list[tuple] = []

    for i in range(60, len(df) - 5):
        bar      = df.iloc[i]
        prev_bar = df.iloc[i - 1]
        close    = float(bar["Close"])

        # ── Maintain unmitigated FVG lists ──────────────────────────────
        if pd.notna(bar["fvg_bull_top"]):
            fvg_bull.append((float(bar["fvg_bull_top"]), float(bar["fvg_bull_bot"]), i))
        if pd.notna(bar["fvg_bear_top"]):
            fvg_bear.append((float(bar["fvg_bear_top"]), float(bar["fvg_bear_bot"]), i))

        # Purge any FVGs that price has now touched (mitigated)
        fvg_bull = [(t,b,dt) for t,b,dt in fvg_bull if not (close >= b and close <= t)]
        fvg_bear = [(t,b,dt) for t,b,dt in fvg_bear if not (close >= b and close <= t)]

        # ── Check open trade exit ───────────────────────────────────────
        if in_trade and cur_trade:
            sl     = cur_trade["stop_loss"]
            target = cur_trade["target"]
            dirn   = cur_trade["direction"]

            hit_sl  = (dirn == "LONG"  and float(bar["Low"])  <= sl)  or \
                      (dirn == "SHORT" and float(bar["High"]) >= sl)
            hit_tp  = (dirn == "LONG"  and float(bar["High"]) >= target) or \
                      (dirn == "SHORT" and float(bar["Low"])  <= target)

            if hit_sl or hit_tp:
                exit_px    = target if hit_tp else sl
                entry      = cur_trade["entry_price"]
                pnl_pct    = ((exit_px - entry) / entry * 100) if dirn == "LONG" \
                              else ((entry - exit_px) / entry * 100)
                pnl_dollars = round((exit_px - entry) * cur_trade["position_size"], 2) if dirn == "LONG" \
                               else round((entry - exit_px) * cur_trade["position_size"], 2)
                equity      = max(equity + pnl_dollars, 0.01)

                cur_trade.update(
                    exit_price    = round(exit_px, 4),
                    pnl_pct       = round(pnl_pct, 2),
                    pnl_dollars   = round(pnl_dollars, 2),
                    account_equity= round(equity, 2),
                    result        = "Target Hit ✅" if hit_tp else "Stopped ❌",
                )
                trades.append(cur_trade)
                in_trade  = False
                cur_trade = None
            continue  # always continue — no new trade opening while in trade

        # ── Rolling 20-bar range for Fib context ───────────────────────
        hi20 = float(df["High"].iloc[i-20:i].max())
        lo20 = float(df["Low"].iloc[i-20:i].min())

        # ── Evaluate LONG ───────────────────────────────────────────────
        sc_long, reasons_long = score_long(bar, prev_bar, close, hi20, lo20, fvg_bull)

        if sc_long >= MIN_SCORE:
            fp   = fib_pos(close, hi20, lo20)
            # Entry: mid of nearest bull FVG if exists, else current close
            if fvg_bull:
                ft, fb, _ = fvg_bull[-1]
                entry = round((ft + fb) / 2, 4)
            else:
                entry = round(close, 4)

            sl_ref = float(bar["sweep_lo_level"]) if pd.notna(bar["sweep_lo_level"]) \
                     else float(df["Low"].iloc[i-5:i].min())
            sl     = round(sl_ref * 0.998, 4)
            target = round(entry + abs(entry - sl) * RR_LONG, 4)
            trigger = " → ".join(reasons_long)
            context = f"Bullish Bias | 1H SMC+TA | Fib {fp:.2f} | Score {sc_long}/8"

            dollar_risk = round(equity * RISK_PER_TRADE, 2)
            sl_distance = abs(entry - sl)
            pos_size = dollar_risk / sl_distance if sl_distance > 0 else 0

            cur_trade = dict(
                date_time     = str(df.index[i]),
                market_context= context,
                trade_type    = "Swing" if abs(target-entry)/entry > 0.03 else "Intraday",
                direction     = "LONG",
                trigger_why   = trigger,
                entry_price   = entry,
                stop_loss      = sl,
                target        = target,
                risk_reward   = RR_LONG,
                confluence_score = sc_long,
                trade_balance_before = round(equity, 2),
                dollar_risk    = dollar_risk,
                position_size  = round(pos_size, 6),
            )
            in_trade = True
            continue

        # ── Evaluate SHORT ──────────────────────────────────────────────
        sc_short, reasons_short = score_short(bar, prev_bar, close, hi20, lo20, fvg_bear)

        if sc_short >= MIN_SCORE:
            fp   = fib_pos(close, hi20, lo20)
            if fvg_bear:
                ft, fb, _ = fvg_bear[-1]
                entry = round((ft + fb) / 2, 4)
            else:
                entry = round(close, 4)

            sl_ref = float(bar["sweep_hi_level"]) if pd.notna(bar["sweep_hi_level"]) \
                     else float(df["High"].iloc[i-5:i].max())
            sl     = round(sl_ref * 1.002, 4)
            target = round(entry - abs(sl - entry) * RR_SHORT, 4)
            if target <= 0:
                continue

            trigger = " → ".join(reasons_short)
            context = f"Bearish Bias | 1H SMC+TA | Fib {fp:.2f} | Score {sc_short}/8"

            dollar_risk = round(equity * RISK_PER_TRADE, 2)
            sl_distance = abs(sl - entry)
            pos_size = dollar_risk / sl_distance if sl_distance > 0 else 0

            cur_trade = dict(
                date_time     = str(df.index[i]),
                market_context= context,
                trade_type    = "Swing" if abs(entry-target)/entry > 0.03 else "Intraday",
                direction     = "SHORT",
                trigger_why   = trigger,
                entry_price   = entry,
                stop_loss      = sl,
                target        = target,
                risk_reward   = RR_SHORT,
                confluence_score = sc_short,
                trade_balance_before = round(equity, 2),
                dollar_risk    = dollar_risk,
                position_size  = round(pos_size, 6),
            )
            in_trade = True

    # ── Close any open trade at last bar ──────────────────────────────
    if in_trade and cur_trade:
        last    = df.iloc[-1]
        exit_px = float(last["Close"])
        entry   = cur_trade["entry_price"]
        dirn    = cur_trade["direction"]
        pnl_pct = ((exit_px - entry) / entry * 100) if dirn == "LONG" \
                   else ((entry - exit_px) / entry * 100)
        pnl_dollars = round((exit_px - entry) * cur_trade["position_size"], 2) if dirn == "LONG" \
                       else round((entry - exit_px) * cur_trade["position_size"], 2)
        cur_trade.update(
            exit_price    = round(exit_px, 4),
            pnl_pct       = round(pnl_pct, 2),
            pnl_dollars   = round(pnl_dollars, 2),
            account_equity= round(equity + pnl_dollars, 2),
            result        = "Open at End ⏳",
        )
        trades.append(cur_trade)

    stats = _compute_stats(trades, df_daily, initial_capital)
    return trades, stats


# ─────────────────────────────────────────────
# PERFORMANCE ANALYTICS
# ─────────────────────────────────────────────
def _compute_stats(trades: list[dict], df_daily: pd.DataFrame, init: float) -> dict:
    completed = [t for t in trades if t.get("result","").startswith(("Target","Stopped"))]
    if not completed:
        return {"error": "No completed trades found. Try a wider date range or lower MIN_SCORE."}

    wins   = [t for t in completed if "Target" in t["result"]]
    losses = [t for t in completed if "Stopped" in t["result"]]

    gross_profit = sum(t["pnl_dollars"] for t in wins)
    gross_loss   = abs(sum(t["pnl_dollars"] for t in losses)) or 1.0

    eq_curve = [init]
    for t in completed:
        eq_curve.append(eq_curve[-1] + t["pnl_dollars"])

    peak = eq_curve[0]
    max_dd_pct = 0.0
    max_dd_usd = 0.0
    for eq in eq_curve:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak * 100
        dd_usd = peak - eq
        if dd > max_dd_pct: max_dd_pct = dd
        if dd_usd > max_dd_usd: max_dd_usd = dd_usd

    ret = pd.Series(eq_curve).pct_change().dropna()
    sharpe = float((ret.mean() / ret.std() * (252**0.5)) if ret.std() > 0 else 0)

    final_eq   = eq_curve[-1]
    total_ret  = (final_eq - init) / init * 100
    bnh_start  = float(df_daily["Close"].iloc[0])
    bnh_end    = float(df_daily["Close"].iloc[-1])
    bnh_ret    = (bnh_end - bnh_start) / bnh_start * 100
    avg_score  = round(sum(t.get("confluence_score", 0) for t in completed) / len(completed), 1)

    return {
        "total_trades":        len(completed),
        "wins":                len(wins),
        "losses":              len(losses),
        "win_rate_pct":        round(len(wins) / len(completed) * 100, 1),
        "profit_factor":       round(gross_profit / gross_loss, 2),
        "max_drawdown_pct":    round(max_dd_pct, 2),
        "max_drawdown_usd":    round(max_dd_usd, 2),
        "sharpe_ratio":        round(sharpe, 2),
        "total_return_pct":    round(total_ret, 2),
        "final_equity_usd":    round(final_eq, 2),
        "buy_hold_return_pct": round(bnh_ret, 2),
        "alpha_vs_bnh_pct":    round(total_ret - bnh_ret, 2),
        "avg_confluence_score": avg_score,
    }


# ─────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────
def generate_excel_report(trades: list[dict], stats: dict, symbol: str) -> bytes:
    try:
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.chart import LineChart, Reference
    except ImportError:
        raise ImportError("openpyxl required. Run: pip install openpyxl")

    wb  = openpyxl.Workbook()
    ws  = wb.active
    ws.title = "SMC Forensic Trade Log"

    DARK   = PatternFill("solid", fgColor="0D1117")
    GBG    = PatternFill("solid", fgColor="0D3321")
    RBG    = PatternFill("solid", fgColor="3D0D0D")
    CYAN   = Font(color="00FFFF", bold=True)
    GFONT  = Font(color="00FF88")
    RFONT  = Font(color="FF4444")
    WFONT  = Font(color="FFFFFF", bold=True)
    GRAY   = Font(color="888888")
    thin   = Side(style="thin", color="333333")
    BRD    = Border(left=thin, right=thin, top=thin, bottom=thin)
    CENTER = Alignment(horizontal="center", vertical="center")
    LEFT   = Alignment(horizontal="left",   vertical="center", wrap_text=True)

    headers = ["Date_Time","Market_Context","Type","Direction","Trigger_Why",
               "Score", "Balance_Before", "Dollar_Risk", "Entry", "SL", "Target", "Pos_Size_Units",
               "Exit", "PnL_%", "Net_PnL_USD", "Cumulative_Equity", "Result"]
    col_widths = [22,40,10,10,80,7,16,14,14,14,14,16,14,10,14,18,18]

    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = DARK; c.font = CYAN; c.alignment = CENTER; c.border = BRD
    ws.row_dimensions[1].height = 28

    for ri, trade in enumerate(trades, 2):
        result  = trade.get("result", "")
        is_win  = "Target" in result
        is_loss = "Stopped" in result
        bg      = GBG if is_win else RBG if is_loss else DARK

        row = [
            trade.get("date_time",""),
            trade.get("market_context",""),
            trade.get("trade_type",""),
            trade.get("direction",""),
            trade.get("trigger_why",""),
            trade.get("confluence_score",""),
            trade.get("trade_balance_before",""),
            trade.get("dollar_risk",""),
            trade.get("entry_price",""),
            trade.get("stop_loss",""),
            trade.get("target",""),
            trade.get("position_size",""),
            trade.get("exit_price",""),
            trade.get("pnl_pct",""),
            trade.get("pnl_dollars",""),
            trade.get("account_equity",""),
            result,
        ]
        for ci, val in enumerate(row, 1):
            c = ws.cell(row=ri, column=ci, value=val)
            c.fill = bg; c.border = BRD
            c.alignment = LEFT if ci in (2,5) else Alignment(horizontal="right", vertical="center")
            if ci == 14:   # PnL%
                c.font = GFONT if (val or 0) > 0 else RFONT
                c.number_format = "+0.00%;-0.00%"
            elif ci in (7, 8, 15):   # Balance_Before, Dollar_Risk, Net_PnL_USD
                c.font = GFONT if (val or 0) > 0 else RFONT
                if ci == 8: c.font = RFONT # Risk is red
                c.number_format = '"$"#,##0.00'
            elif ci == 12: # Pos size units
                c.font = WFONT; c.number_format = '#,##0.0000'
            elif ci == 16: # Cum Equity
                c.font = WFONT; c.number_format = '"$"#,##0.00'
            else:
                c.font = GRAY
        ws.row_dimensions[ri].height = 50

    for ci, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.freeze_panes = "A2"

    # Stats sheet
    ws2 = wb.create_sheet("Performance Analytics")
    stat_rows = [
        ("── SMC + TA Confluence Backtest ──", ""),
        ("Symbol",           symbol),
        ("Period",           "Custom Range"),
        ("Initial Capital",  f'${stats.get("final_equity_usd",0) / (1 + (stats.get("total_return_pct",0)/100)):,.2f}'),
        ("Min Confluence Score", f"{MIN_SCORE}/8"),
        ("",""),
        ("── Trade Stats ──", ""),
        ("Total Trades",     stats.get("total_trades",0)),
        ("Wins",             stats.get("wins",0)),
        ("Losses",           stats.get("losses",0)),
        ("Win Rate",         f"{stats.get('win_rate_pct',0):.1f}%"),
        ("Avg Confluence Score", f"{stats.get('avg_confluence_score',0)}/8"),
        ("",""),
        ("── Performance ──", ""),
        ("Total Return",     f"{stats.get('total_return_pct',0):.2f}%"),
        ("Final Equity",     f"${stats.get('final_equity_usd',0):,.2f}"),
        ("Profit Factor",    f"{stats.get('profit_factor',0):.2f}x"),
        ("Max Drawdown (Pct)",  f"{stats.get('max_drawdown_pct',0):.2f}%"),
        ("Max Drawdown (USD)",  f"${stats.get('max_drawdown_usd',0):,.2f}"),
        ("Sharpe Ratio",     f"{stats.get('sharpe_ratio',0):.2f}"),
        ("",""),
        ("── vs Buy & Hold ──", ""),
        ("B&H Return",       f"{stats.get('buy_hold_return_pct',0):.2f}%"),
        ("SMC Alpha",        f"{stats.get('alpha_vs_bnh_pct',0):+.2f}%"),
    ]
    for ri, (label, val) in enumerate(stat_rows, 1):
        lc = ws2.cell(row=ri, column=1, value=label)
        vc = ws2.cell(row=ri, column=2, value=val)
        if label.startswith("──"):
            lc.font = CYAN; lc.fill = DARK; vc.fill = DARK
        else:
            lc.font = GRAY; vc.font = WFONT
            lc.fill = vc.fill = PatternFill("solid", fgColor="111827")
        lc.alignment = vc.alignment = Alignment(vertical="center")
        ws2.row_dimensions[ri].height = 22
    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 22
    ws2.sheet_view.showGridLines = False

    # Equity curve sheet
    ws3 = wb.create_sheet("Equity Curve")
    ws3.append(["Trade #", "Equity ($)"])
    ws3.cell(1,1).font = CYAN; ws3.cell(1,1).fill = DARK
    ws3.cell(1,2).font = CYAN; ws3.cell(1,2).fill = DARK
    eq = INITIAL_EQUITY
    for i, t in enumerate(trades, 1):
        eq = t.get("account_equity", eq)
        ws3.append([i, eq])

    chart = LineChart()
    chart.title = "SMC + TA Equity Curve"
    chart.style = 10
    chart.y_axis.title = "Equity ($)"
    chart.x_axis.title = "Trade #"
    chart.width = 26; chart.height = 15
    data_ref = Reference(ws3, min_col=2, min_row=1, max_row=len(trades)+1)
    cat_ref  = Reference(ws3, min_col=1, min_row=2, max_row=len(trades)+1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cat_ref)
    chart.series[0].graphicalProperties.line.solidFill = "00FF88"
    chart.series[0].graphicalProperties.line.width = 8000
    ws3.add_chart(chart, "D2")
    ws3.column_dimensions["A"].width = 12
    ws3.column_dimensions["B"].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
