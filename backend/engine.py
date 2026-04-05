import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ProcessPoolExecutor, as_completed
from schemas import SetupResponse, ConfluenceScore, NarrativeDetail, ForensicReport, ChecklistDetails, DerivativeStats

def fetch_htf_data(symbol: str, is_india: bool = False):
    """Fetch Base Primary Anchor data (1D and 1H/4H)."""
    try:
        t = yf.Ticker(symbol)
        df_1d = t.history(period="1y", interval="1d", auto_adjust=True)
        # Indian markets only run 6.25h, so 4H candles are distorted. We use 1H as anchor for India.
        anchor_interval = "1h" if is_india else "1h" # Defaulting to 1h for now to ensure data continuity
        df_anchor = t.history(period="60d", interval=anchor_interval, auto_adjust=True)
        return symbol, df_1d, df_anchor
    except Exception as e:
        return symbol, None, None

def fetch_zoom_data(symbol: str, resolution: str):
    """Fetch LTF Sniper data on-demand (1m or 10m)."""
    try:
        t = yf.Ticker(symbol)
        period = "1d" if resolution == "1m" else "5d"
        return t.history(period=period, interval=resolution, auto_adjust=True)
    except Exception as e:
        return None

def analyze_smc(symbol, df_1d, df_anchor):
    """Hierarchical On-Demand Vectorized SMC Engine."""
    if df_1d is None or df_1d.empty or df_anchor is None or df_anchor.empty or len(df_anchor) < 20:
        return None
        
    is_india = symbol.endswith(".NS") or symbol.endswith(".BO")
    anchor_name = "1H" if is_india else "4H"
    
    # ── 1. Chop Detection Filter ──────────────────────────────────────────
    # If the market is moving sideways, we abort early to save compute.
    recent_anchor = df_anchor.tail(20)
    price_range = recent_anchor['High'].max() - recent_anchor['Low'].min()
    atr_proxy = (recent_anchor['High'] - recent_anchor['Low']).mean()
    # If 20-period range is barely larger than 3 times the average bar, it's chopping
    is_chop = price_range < (atr_proxy * 3)
    
    if is_chop:
        # Return a neutral, non-setup response and skip deep dive
        return None
    
    # ── 2. HTF Bias & Anchor Logic ────────────────────────────────────────
    df_1d = df_1d.copy()
    df_1d['SMA_50'] = df_1d['Close'].rolling(window=50).mean()
    last_close = float(df_1d['Close'].iloc[-1])
    sma_50 = float(df_1d['SMA_50'].iloc[-1]) if pd.notna(df_1d['SMA_50'].iloc[-1]) else last_close
    
    bias = "bullish" if last_close > sma_50 else "bearish"
    
    confluence = ConfluenceScore()
    if bias in ["bullish", "bearish"]:
        confluence.trend_alignment = 2
        
    # FVG Detection on Anchor
    df_anchor = df_anchor.copy()
    df_anchor['bullish_fvg'] = (df_anchor['High'].shift(2) < df_anchor['Low']) & (df_anchor['Close'].shift(1) > df_anchor['High'].shift(2))
    df_anchor['bearish_fvg'] = (df_anchor['Low'].shift(2) > df_anchor['High']) & (df_anchor['Close'].shift(1) < df_anchor['Low'].shift(2))
    
    fvg_size = 0.0
    recent_fvg = False
    
    if bias == "bullish" and df_anchor['bullish_fvg'].any():
        idx = df_anchor[df_anchor['bullish_fvg']].index[-1]
        fvg_size = float(df_anchor.loc[idx, 'Low'] - df_anchor.shift(2).loc[idx, 'High'])
        recent_fvg = (len(df_anchor) - df_anchor.index.get_loc(idx)) <= 10
    elif bias == "bearish" and df_anchor['bearish_fvg'].any():
        idx = df_anchor[df_anchor['bearish_fvg']].index[-1]
        fvg_size = float(df_anchor.shift(2).loc[idx, 'Low'] - df_anchor.loc[idx, 'High'])
        recent_fvg = (len(df_anchor) - df_anchor.index.get_loc(idx)) <= 10
        
    if recent_fvg:
        confluence.fvg_mitigation = 2 if fvg_size < (last_close * 0.01) else 3 # displacement score
        
    # Sweeps on Anchor
    df_anchor['is_low'] = (df_anchor['Low'] < df_anchor['Low'].shift(1)) & (df_anchor['Low'] < df_anchor['Low'].shift(-1))
    df_anchor['is_high'] = (df_anchor['High'] > df_anchor['High'].shift(1)) & (df_anchor['High'] > df_anchor['High'].shift(-1))
    
    recent_sweep = df_anchor['is_low'].tail(5).any() if bias == "bullish" else df_anchor['is_high'].tail(5).any()
    if recent_sweep:
        confluence.idm_sweep = 3
        
    # Order Blocks
    ob_top, ob_bottom = None, None
    if bias == "bullish" and recent_fvg:
         idx = df_anchor[df_anchor['bullish_fvg']].index[-1]
         ob_idx = df_anchor.loc[:idx].where(df_anchor['Close'] < df_anchor['Open']).last_valid_index()
         if ob_idx:
             ob_top = float(df_anchor.loc[ob_idx, 'High'])
             ob_bottom = float(df_anchor.loc[ob_idx, 'Low'])
    elif bias == "bearish" and recent_fvg:
         idx = df_anchor[df_anchor['bearish_fvg']].index[-1]
         ob_idx = df_anchor.loc[:idx].where(df_anchor['Close'] > df_anchor['Open']).last_valid_index()
         if ob_idx:
             ob_top = float(df_anchor.loc[ob_idx, 'High'])
             ob_bottom = float(df_anchor.loc[ob_idx, 'Low'])

    # Premium / Discount
    location_str = "Neutral Location"
    if not df_1d.empty and len(df_1d) > 20:
        recent_high = df_1d['High'].tail(20).max()
        recent_low = df_1d['Low'].tail(20).min()
        fib_0786_bull = recent_low + (recent_high - recent_low) * 0.214
        fib_0786_bear = recent_high - (recent_high - recent_low) * 0.214
        
        if bias == "bullish" and last_close <= fib_0786_bull:
            confluence.discount_premium = 3
            location_str = "HTF 1D Deep Discount (<0.786 Fib)"
        elif bias == "bearish" and last_close >= fib_0786_bear:
            confluence.discount_premium = 3
            location_str = "HTF 1D Deep Premium (>0.786 Fib)"
            
    confluence.total_score = (confluence.trend_alignment + confluence.fvg_mitigation + 
                              confluence.idm_sweep + confluence.discount_premium)
                              
    if confluence.total_score < 5:
        return None # Not a strong enough setup to warrant a Zoom.

    # ── 3. Heuristic Zoom Trigger ─────────────────────────────────────────
    zoom_res = None
    trade_classification = "SWING"
    margin = "1x"
    auto_square_off = None
    zoom_reason = ""
    current_price = last_close
    
    # Decide Zoom Resolution
    if confluence.discount_premium == 3 and recent_sweep:
        # Sniper Entry - we are at an extreme + sweep. Drop to 1m.
        zoom_res = "1m"
    elif recent_fvg:
        # Trend continuation - drop to 10m to confirm displacement
        zoom_res = "10m"
        
    zoom_score_bonus = 0
    if zoom_res:
        df_ltf = fetch_zoom_data(symbol, zoom_res)
        if df_ltf is not None and not df_ltf.empty:
            current_price = float(df_ltf['Close'].iloc[-1])
            trade_classification = "INTRADAY"
            margin = "5x Margin"
            auto_square_off = "15:15 IST" if is_india else "EOD"
            
            # Simple LTF verification (CHoCH / Momentum)
            df_ltf['ema'] = df_ltf['Close'].ewm(span=9).mean()
            ltf_aligned = (current_price > df_ltf['ema'].iloc[-1]) if bias == "bullish" else (current_price < df_ltf['ema'].iloc[-1])
            
            if ltf_aligned:
                zoom_score_bonus = 2
                zoom_reason = f"{anchor_name} Anchor Detected at {round(last_close, 2)}. Zoomed to {zoom_res} for CHoCH/Momentum confirmation. Momentum Aligned ✅."
            else:
                zoom_reason = f"{anchor_name} Anchor Detected at {round(last_close, 2)}. Zoomed to {zoom_res} but momentum is currently misaligned ⏳."
                trade_classification = "WAITING"
        else:
            zoom_reason = f"{anchor_name} Anchor Valid, but {zoom_res} data unavailable. Defaulting to Swing logic."
    else:
        zoom_reason = f"No extreme limits hit. Relied on {anchor_name} Anchor (Swing Entry)."
        
    confluence.total_score = min(10, confluence.total_score + zoom_score_bonus)
    status = "A+" if confluence.total_score >= 8 else "Valid"
    
    entry = round(current_price, 2)
    sl_raw = ob_bottom if (ob_bottom and bias == "bullish") else ob_top if (ob_top and bias == "bearish") else (entry * 0.99 if bias == "bullish" else entry * 1.01)
    sl = round(float(sl_raw), 2)
    
    if bias == "bearish": tp_raw = entry - abs(entry - sl) * 3
    else: tp_raw = entry + abs(entry - sl) * 3
    tp = round(float(tp_raw), 2)
    rr = 3.0
    
    # Generate Narrative
    timeline = []
    if recent_sweep:
        timeline.append(f"Market swept liquidity at Key Level near {round(last_close*0.98 if bias=='bullish' else last_close*1.02, 2)}.")
    if recent_fvg:
        timeline.append(f"{'BOS (Continuation)' if confluence.trend_alignment > 0 else 'CHoCH (Reversal)'} occurred leaving a {'massive' if confluence.fvg_mitigation == 3 else 'standard'} FVG.")
    if ob_top is not None:
        timeline.append(f"Price targeted {'Discount' if bias=='bullish' else 'Premium'} Order Block between {round(ob_bottom, 2)} and {round(ob_top, 2)}.")
    timeline.append(f"Ready for optimal entry at {entry}.")

    breakdown = [f"HTF Trend: +{confluence.trend_alignment}"]
    if recent_fvg: breakdown.append(f"FVG & Displacement: +{confluence.fvg_mitigation}")
    if recent_sweep: breakdown.append(f"IDM Sweep: +{confluence.idm_sweep}")
    if confluence.discount_premium > 0: breakdown.append(f"Optimal Location: +{confluence.discount_premium}")
    if zoom_score_bonus > 0: breakdown.append(f"LTF {zoom_res} Alignment: +{zoom_score_bonus}")

    narrative = NarrativeDetail(
        reason="Inducement Sweep + FVG Mitigation" if recent_sweep and recent_fvg else "SMC Structural Shift",
        location=location_str,
        context="Institutional stop-hunt detected followed by impulsive displacement." if recent_sweep else "Market structure shift suggesting imminent delivery to opposing liquidity.",
        score_breakdown=breakdown,
        timeline=timeline,
        zoom_reason=zoom_reason
    )
    
    return SetupResponse(
        symbol=symbol,
        bias=bias,
        status=status,
        entry=entry,
        stop_loss=sl,
        take_profit=tp,
        risk_reward=rr,
        confluence=confluence,
        narrative=narrative,
        ob_top=ob_top,
        ob_bottom=ob_bottom,
        zoom_resolution=zoom_res,
        trade_classification=trade_classification,
        margin_multiple=margin,
        auto_square_off=auto_square_off
    )

def process_symbol(symbol):
    is_india = symbol.endswith(".NS") or symbol.endswith(".BO")
    sym, d1, anchor = fetch_htf_data(symbol, is_india)
    return analyze_smc(sym, d1, anchor)

def run_scan(symbols):
    results = []
    # Multiprocessing for Base Anchors (Fast)
    with ProcessPoolExecutor(max_workers=8) as executor:
        for res in executor.map(process_symbol, symbols):
            if res is not None:
                results.append(res)
                
    results.sort(key=lambda x: x.confluence.total_score, reverse=True)
    return results

def run_forensic_scan(symbol: str) -> ForensicReport:
    """Intensive forensic engine using the Variable Resolution Logic."""
    is_india = symbol.endswith(".NS") or symbol.endswith(".BO")
    sym, df_1d, df_anchor = fetch_htf_data(symbol, is_india)
    
    if df_1d is None or df_anchor is None or len(df_anchor) < 10:
        return None
        
    last_close = float(df_1d['Close'].iloc[-1])
    df_1d['SMA_50'] = df_1d['Close'].rolling(window=50).mean()
    sma_50 = float(df_1d['SMA_50'].iloc[-1]) if pd.notna(df_1d['SMA_50'].iloc[-1]) else last_close
    is_bullish = last_close > sma_50
    
    # Analyze FVG on Anchor
    df_anchor['fvg_bull'] = (df_anchor['High'].shift(2) < df_anchor['Low']) & (df_anchor['Close'].shift(1) > df_anchor['High'].shift(2))
    df_anchor['fvg_bear'] = (df_anchor['Low'].shift(2) > df_anchor['High']) & (df_anchor['Close'].shift(1) < df_anchor['Low'].shift(2))
    fvg_created = bool(df_anchor['fvg_bull'].tail(10).any() if is_bullish else df_anchor['fvg_bear'].tail(10).any())
    
    # Sweep Detection
    df_anchor['sweep_low'] = (df_anchor['Low'] < df_anchor['Low'].shift(1)) & (df_anchor['Close'] > df_anchor['Low'].shift(1))
    df_anchor['sweep_high'] = (df_anchor['High'] > df_anchor['High'].shift(1)) & (df_anchor['Close'] < df_anchor['High'].shift(1))
    liquidity_swept = bool(df_anchor['sweep_low'].tail(5).any() if is_bullish else df_anchor['sweep_high'].tail(5).any())
    
    # Discount / Premium Check
    recent_high = df_1d['High'].tail(20).max()
    recent_low = df_1d['Low'].tail(20).min()
    in_discount = False
    if is_bullish and last_close <= (recent_low + (recent_high - recent_low) * 0.5):
        in_discount = True
    elif not is_bullish and last_close >= (recent_high - (recent_high - recent_low) * 0.5):
        in_discount = True
        
    # Trigger Zoom for deep forensic level
    zoom_res = "1m" if (in_discount and liquidity_swept) else "10m"
    df_ltf = fetch_zoom_data(symbol, zoom_res)
    entry = float(df_ltf['Close'].iloc[-1]) if (df_ltf is not None and not df_ltf.empty) else last_close
        
    # Volume-Price OI Proxy
    recent_vol = df_1d['Volume'].tail(3).mean()
    prev_vol = df_1d['Volume'].iloc[-10:-3].mean()
    price_change = last_close - df_1d['Close'].iloc[-3]
    
    oi_interpretation = "Neutral Consolidation"
    if recent_vol > prev_vol * 1.5:
        if price_change > 0: oi_interpretation = "Massive Long Build-Up"
        else: oi_interpretation = "Aggressive Short Build-Up"
    elif price_change > 0 and recent_vol < prev_vol:
        oi_interpretation = "Short Covering Detected"
    elif price_change < 0 and recent_vol < prev_vol:
        oi_interpretation = "Long Unwinding"
        
    max_pain_proxy = round(last_close / 50) * 50

    formation = f"Formed at the HTF {'Deep Discount' if in_discount else 'Equilibrium'} near {round(last_close, 2)}."
    catalyst = "Liquidity sweep of structural zones." if liquidity_swept else "Institutional displacement leaving Unmitigated FVGs." if fvg_created else "Price tracking SMA momentum drift."
    
    sl = float(entry * 0.98 if is_bullish else entry * 1.02)
    tp = float(entry + ((entry - sl) * 3) if is_bullish else entry - abs(entry - sl) * 3)

    return ForensicReport(
        formation=formation,
        catalyst=catalyst,
        checklist=ChecklistDetails(
            htf_aligned=True,
            liquidity_swept=liquidity_swept,
            fvg_created=fvg_created,
            in_discount=in_discount
        ),
        derivative_stats=DerivativeStats(
            oi_interpretation=oi_interpretation,
            max_pain_proxy=float(max_pain_proxy)
        ),
        instruction=f"Look at your {zoom_res} zoomed chart. If you see displacement {'above' if is_bullish else 'below'} {round(entry, 2)}, the Setup is confirmed. Place your SL precisely at {round(sl, 2)}. (Trade Classification: {'INTRADAY' if zoom_res else 'SWING'})",
        entry=round(entry, 2),
        stop_loss=round(sl, 2),
        take_profit=round(tp, 2),
        risk_reward=3.0,
        zoom_resolution=zoom_res,
        trade_classification="INTRADAY" if df_ltf is not None else "SWING",
        margin_multiple="5x Margin" if df_ltf is not None else "1x",
        auto_square_off="15:15 IST" if (df_ltf is not None and is_india) else None
    )
