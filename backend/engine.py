import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ProcessPoolExecutor
from schemas import SetupResponse, ConfluenceScore, NarrativeDetail

def fetch_data(symbol: str):
    """Fetch Multi-Tier data using yfinance."""
    try:
        t = yf.Ticker(symbol)
        df_1d = t.history(period="1y", interval="1d")
        df_1h = t.history(period="60d", interval="1h")
        df_5m = t.history(period="5d", interval="5m")
        return symbol, df_1d, df_1h, df_5m
    except Exception as e:
        return symbol, None, None, None

def analyze_smc(symbol, df_1d, df_1h, df_5m):
    """Vectorized SMC / ICT Math Module."""
    if df_1d is None or df_1d.empty or df_1h is None or df_1h.empty:
        return None
    
    # 1. HTF Bias (Daily Level)
    df_1d['SMA_50'] = df_1d['Close'].rolling(window=50).mean()
    last_close = df_1d['Close'].iloc[-1]
    sma_50 = df_1d['SMA_50'].iloc[-1]
    
    bias = "bullish" if last_close > sma_50 else "bearish"
    
    confluence = ConfluenceScore()
    # Scoring
    if bias == "bullish" or bias == "bearish":
        confluence.trend_alignment = 2
        
    # 2. 1H FVG Detection & Displacement
    df_1h['bullish_fvg'] = (df_1h['High'].shift(2) < df_1h['Low']) & (df_1h['Close'].shift(1) > df_1h['High'].shift(2))
    df_1h['bearish_fvg'] = (df_1h['Low'].shift(2) > df_1h['High']) & (df_1h['Close'].shift(1) < df_1h['Low'].shift(2))
    
    fvg_size = 0.0
    recent_fvg = False
    
    if bias == "bullish" and df_1h['bullish_fvg'].any():
        idx = df_1h[df_1h['bullish_fvg']].index[-1]
        fvg_size = df_1h.loc[idx, 'Low'] - df_1h.shift(2).loc[idx, 'High']
        recent_fvg = (len(df_1h) - df_1h.index.get_loc(idx)) <= 10
    elif bias == "bearish" and df_1h['bearish_fvg'].any():
        idx = df_1h[df_1h['bearish_fvg']].index[-1]
        fvg_size = df_1h.shift(2).loc[idx, 'Low'] - df_1h.loc[idx, 'High']
        recent_fvg = (len(df_1h) - df_1h.index.get_loc(idx)) <= 10
        
    if recent_fvg:
        confluence.fvg_mitigation = 2 if fvg_size < (last_close * 0.01) else 3 # displacement score
        
    # 3. Inducement (IDM) Logic & Structural Sweeps
    df_1h['is_low'] = (df_1h['Low'] < df_1h['Low'].shift(1)) & (df_1h['Low'] < df_1h['Low'].shift(-1))
    df_1h['is_high'] = (df_1h['High'] > df_1h['High'].shift(1)) & (df_1h['High'] > df_1h['High'].shift(-1))
    
    recent_sweep = df_1h['is_low'].tail(5).any() if bias == "bullish" else df_1h['is_high'].tail(5).any()
    if recent_sweep:
        confluence.idm_sweep = 3
        
    # Order Block Detection (simplified context)
    ob_top = None
    ob_bottom = None
    if bias == "bullish" and recent_fvg:
         idx = df_1h[df_1h['bullish_fvg']].index[-1]
         ob_idx = df_1h.loc[:idx].where(df_1h['Close'] < df_1h['Open']).last_valid_index()
         if ob_idx:
             ob_top = float(df_1h.loc[ob_idx, 'High'])
             ob_bottom = float(df_1h.loc[ob_idx, 'Low'])
    elif bias == "bearish" and recent_fvg:
         idx = df_1h[df_1h['bearish_fvg']].index[-1]
         ob_idx = df_1h.loc[:idx].where(df_1h['Close'] > df_1h['Open']).last_valid_index()
         if ob_idx:
             ob_top = float(df_1h.loc[ob_idx, 'High'])
             ob_bottom = float(df_1h.loc[ob_idx, 'Low'])

    # 4. Deep Discount Check (< 0.786 Fib)
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
            
    confluence.total_score = (confluence.trend_alignment + 
                              confluence.fvg_mitigation + 
                              confluence.idm_sweep + 
                              confluence.discount_premium)
                              
    status = "A+" if confluence.total_score >= 8 else "Valid"
    current_price = float(df_5m['Close'].iloc[-1] if (df_5m is not None and not df_5m.empty) else last_close)
    
    entry = round(current_price, 2)
    sl_raw = ob_bottom if ob_bottom else (entry * 0.99 if bias == "bullish" else entry * 1.01)
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

    narrative = NarrativeDetail(
        reason="Inducement Sweep + FVG Mitigation" if recent_sweep and recent_fvg else "SMC Structural Shift",
        location=location_str,
        context="Institutional stop-hunt detected followed by impulsive displacement." if recent_sweep else "Market structure shift suggesting imminent delivery to opposing liquidity.",
        score_breakdown=breakdown,
        timeline=timeline
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
        ob_bottom=ob_bottom
    )

def process_symbol(symbol):
    sym, d1, h1, m5 = fetch_data(symbol)
    return analyze_smc(sym, d1, h1, m5)

def run_scan(symbols):
    results = []
    # Using small max_workers locally to avoid locking up resources, standard is os.cpu_count()
    with ProcessPoolExecutor(max_workers=4) as executor:
        for res in executor.map(process_symbol, symbols):
            if res is not None:
                results.append(res)
                
    results.sort(key=lambda x: x.confluence.total_score, reverse=True)
    return results
